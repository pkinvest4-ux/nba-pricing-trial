"""Price NBA games using only what was known by the end of the day before, and grade the price
against the closing line.

How it works, in plain words:
- Every team has a rating in points, and every player a rating: how many points per 48 minutes he
  adds, learned mostly from closing lines. Predicted home margin = home rating - away rating +
  home-court advantage + the strength gap between the expected lineups, plus adjustments known the
  night before:
  a team on the second night of a back-to-back, and regulars listed out on the injury report.
- The model walks through the seasons one day at a time. It prices every game on a day first,
  and only then learns from that day's results and closing lines. So no game ever sees its own
  result, its own line, or anything from game day.
- Answer key: one book's pre-game closing spread as recorded by ESPN (ESPN BET; DraftKings in
  2025-26 after ESPN changed partners). Pinnacle's history is not available for free, and
  SportsbookReview's "latest" lines turned out to include in-game odds, so they are not used.
- Settings are chosen on 2024-25 only. 2025-26 is the test.
"""
import json, math, os, random, statistics as st, unicodedata
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from common import team

ET = ZoneInfo("America/New_York")
TUNE, TEST = "2024-25", "2025-26"
MAX_SPREAD = 30  # sanity rule: no NBA spread is bigger; ESPN once stored prices (-110) in this field


def key_book(season):
    """The one book graded against in each season: its pre-game close as recorded by ESPN.
    ESPN switched partners from ESPN BET to DraftKings during 2025-26, so that season uses
    DraftKings where ESPN recorded it and ESPN BET for the early games."""
    return ("DraftKings", "ESPN BET") if season == "2025-26" else ("ESPN BET",)


def clean(x):
    return x if x is not None and abs(x) <= MAX_SPREAD else None


def american_to_prob(odds):
    return -odds / (-odds + 100) if odds < 0 else 100 / (odds + 100)


def no_vig(home, away):
    if not home or not away:
        return None
    ph, pa = american_to_prob(home), american_to_prob(away)
    return ph / (ph + pa) if 1.0 < ph + pa < 1.15 else None  # real two-way markets add up to a bit over 100%


def local_day(g):
    return datetime.fromisoformat(g["date"].replace("Z", "+00:00")).astimezone(ET).date()


def load():
    games = [json.loads(l) for l in open("data/games.jsonl")]
    games.sort(key=lambda g: g["date"])
    odds = json.load(open("data/espn_odds.json"))
    for g in games:
        books = odds.get(g["id"], {})
        g["close"] = g["open"] = g["close_prob"] = g["key_book"] = None
        for b in key_book(g["season"]):
            rec = books.get(b) or {}
            if clean(rec.get("close_spread")) is not None:
                g["close"], g["open"] = clean(rec["close_spread"]), clean(rec.get("open_spread"))
                g["close_prob"] = no_vig(rec.get("close_ml_home"), rec.get("close_ml_away"))
                g["key_book"] = b
                break
        # Older seasons have no labelled pre-game close. For the walk-forward test they are graded
        # against Pinnacle's line where ESPN lists it, else ESPN's consensus, else the books' median.
        if g["close"] is None:
            pin = next((clean(r.get("spread")) for name, r in books.items() if "pinnacle" in name.lower()
                        and clean(r.get("spread")) is not None), None)
            cons = clean((books.get("consensus") or {}).get("spread"))
            others = [clean(r.get("spread")) for name, r in books.items()
                      if clean(r.get("spread")) is not None and name != "Opening"]
            for line, source in ((pin, "Pinnacle"), (cons, "ESPN consensus"),
                                 (st.median(others) if others else None, "median of books")):
                if line is not None:
                    g["close"], g["key_book"] = line, source
                    break
        # What the model may LEARN from once a game is over: the same line.
        g["learn_close"] = g["close"]
        g["margin"] = g["home_pts"] - g["away_pts"]
    for season in (TUNE, TEST):
        sg = [g for g in games if g["season"] == season]
        print(f"{season}: graded close for {sum(g['close'] is not None for g in sg)} of {len(sg)} games "
              f"({', '.join(b + ' ' + str(sum(g['key_book'] == b for g in sg)) for b in key_book(season))})")
    add_rest(games)
    add_injuries(games)
    add_roster(games)
    add_lineups(games)
    return games


def game_days(games):
    days, key = [], None
    for g in games:
        d = local_day(g)
        if d != key:
            days.append([])
            key = d
        days[-1].append(g)
    return days


TIMEZONE = {  # hours behind Eastern for each home arena
    "ATL": 0, "BKN": 0, "BOS": 0, "CHA": 0, "CLE": 0, "DET": 0, "IND": 0, "MIA": 0, "NY": 0, "ORL": 0,
    "PHI": 0, "TOR": 0, "WSH": 0, "CHI": 1, "DAL": 1, "HOU": 1, "MEM": 1, "MIL": 1, "MIN": 1, "NO": 1,
    "OKC": 1, "SA": 1, "DEN": 2, "PHX": 2, "UTAH": 2, "GS": 3, "LAC": 3, "LAL": 3, "POR": 3, "SAC": 3}


def add_rest(games):
    """Schedule effects, all public months ahead: second night of a back-to-back, third game in four
    nights, rest-day difference (capped at 3), and time zones crossed since the team's last game."""
    last, history, where = {}, {}, {}
    for g in games:
        d = local_day(g)
        venue = TIMEZONE[g["home"]]
        for side in ("home", "away"):
            t = g[side]
            rest = (d - last[t]).days if t in last else 7
            g[side + "_b2b"] = rest == 1
            recent = [x for x in history.get(t, []) if (d - x).days <= 3]
            g[side + "_3in4"] = len(recent) >= 2
            g[side + "_rest"] = min(rest - 1, 3)
            g[side + "_tz"] = abs(venue - where[t]) if t in where else 0
            last[t] = d
            history.setdefault(t, []).append(d)
            history[t] = history[t][-3:]
            where[t] = venue


BENCH_RATE, MIN_MPG, MAX_MISS = 0.15, 16, 40.0  # from the practice model, chosen there on a tuning season
PRIOR_RATE, PRIOR_MIN = 0.25, 60


def norm(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join("".join(c for c in name.lower() if c.isalpha() or c == " ").split())


STATUS_WEIGHT = {"Out": 1.0, "Doubtful": 0.75, "Questionable": 0.3}


def add_injuries(games):
    """Rotation value each team is missing, from the NBA's official injury report as it stood at the
    end of the day before the game (see fetch_injuries.py). A player's value: Game Score per minute
    above a bench replacement, times his usual minutes, from his team's last 10 games.

    The report archive stops on Dec 21, 2025, so later 2025-26 games have no injury information
    (g["has_report"] is False) and get no adjustment. I also tried 'regulars who sat out the previous
    game' from box scores, which exists for every game: on the tuning season it added nothing, because
    yesterday's closing line, which the ratings already learn from, had priced that absence in."""
    for g in games:
        g["home_miss"] = g["away_miss"] = 0.0
        g["home_back"] = g["away_back"] = 0.0
        g["has_report"] = False
    if not (os.path.exists("data/boxscores.json") and os.path.exists("data/injuries.json")):
        print("no injury data yet")
        return
    box, inj = json.load(open("data/boxscores.json")), json.load(open("data/injuries.json"))
    recent, played, last_team = {}, {}, {}  # team -> last 10 ids; player -> {id: (min, gmsc)}; player -> team
    season_apps, season = {}, None  # player -> this season's (min, gmsc) with his current team
    for day in game_days(games):
        if day[0]["season"] != season:
            season, season_apps = day[0]["season"], {}
        for g in day:
            listed = inj.get(g["id"])
            g["has_report"] = listed is not None
            if listed is not None:
                g["home_back"], g["away_back"] = (returning(g, side, listed, recent, played, last_team, season_apps)
                                                  for side in ("home", "away"))
            for side in ("home", "away"):
                t, miss = g[side], 0.0
                for player, status in (listed or {}).get(t, {}).items():
                    w, pl = STATUS_WEIGHT.get(status, 0.0), norm(player)
                    if not w or last_team.get(pl) != t:  # traded or waived players no longer count
                        continue
                    apps = [played[pl][gid] for gid in recent.get(t, ()) if gid in played.get(pl, {})]
                    if len(apps) < 3:
                        continue
                    mins = sum(m for m, _ in apps)
                    if mins / len(apps) < MIN_MPG:
                        continue
                    rate = (sum(x for _, x in apps) + PRIOR_RATE * PRIOR_MIN) / (mins + PRIOR_MIN)
                    miss += w * max(0.0, rate - BENCH_RATE) * (mins / len(apps))
                g[side + "_miss"] = min(miss, MAX_MISS)
        for g in day:  # learn from the day only after it is priced
            for t in (g["home"], g["away"]):
                for p in box.get(g["id"], {}).get(t, []):
                    if p["min"] > 0:
                        pl = norm(p["name"])
                        if last_team.get(pl) != t:
                            season_apps[pl] = []  # new team: start his record here
                        played.setdefault(pl, {})[g["id"]] = (p["min"], p["gmsc"])
                        last_team[pl] = t
                        season_apps.setdefault(pl, []).append((p["min"], p["gmsc"]))
                recent.setdefault(t, deque(maxlen=10)).append(g["id"])


def returning(g, side, listed, recent, played, last_team, season_apps):
    """Value of regulars who missed recent games but are NOT on tonight's report, so are expected back.
    The team's rating dropped while they were out; this adds them back in proportion to how much of the
    last 10 games they missed. Their value uses this season's games with the team, not just the last 10."""
    t, back = g[side], 0.0
    on_report = {norm(n) for n, s in listed.get(t, {}).items() if STATUS_WEIGHT.get(s)}
    last10 = list(recent.get(t, ()))
    if len(last10) < 5:
        return 0.0
    for pl, apps in season_apps.items():
        if last_team.get(pl) != t or pl in on_report or len(apps) < 10:
            continue
        missed = sum(gid not in played.get(pl, {}) for gid in last10)
        if missed < 2:
            continue
        mins = sum(m for m, _ in apps)
        if mins / len(apps) < MIN_MPG:
            continue
        rate = (sum(x for _, x in apps) + PRIOR_RATE * PRIOR_MIN) / (mins + PRIOR_MIN)
        back += max(0.0, rate - BENCH_RATE) * (mins / len(apps)) * missed / len(last10)
    return min(back, MAX_MISS)


def add_roster(games, window=20, recent_games=3):
    """Expected strength of each team's available players, known the night before: everyone who played
    in at least one of the team's last 3 games THIS season. A player's value is his Game Score per minute
    above a bench replacement, times his usual minutes, from his last 20 games with this team; the
    team's total is scaled to the 240 minutes it actually plays. Box scores of earlier days only."""
    for g in games:
        g["home_roster"] = g["away_roster"] = 0.0
    if not os.path.exists("data/boxscores.json"):
        return
    box = json.load(open("data/boxscores.json"))
    logs, last_team, team_games, season = {}, {}, {}, None  # player -> deque of (min, gmsc) with current team
    for day in game_days(games):
        if day[0]["season"] != season:
            season, team_games = day[0]["season"], {}  # only this season's games define who is available
        for g in day:
            for side in ("home", "away"):
                t = g[side]
                available = {norm(p["name"]) for gid in team_games.get(t, [])[-recent_games:]
                             for p in box.get(gid, {}).get(t, []) if p["min"] > 0}
                players = []
                for pl in available:
                    if last_team.get(pl) != t or len(logs.get(pl, ())) < 3:
                        continue
                    mins = sum(m for m, _ in logs[pl])
                    rate = (sum(x for _, x in logs[pl]) + PRIOR_RATE * PRIOR_MIN) / (mins + PRIOR_MIN)
                    players.append((rate, mins / len(logs[pl])))
                total_min = sum(m for _, m in players)
                scale = 240 / total_min if total_min > 240 else 1.0
                g[side + "_roster"] = sum((r - BENCH_RATE) * m * scale for r, m in players)
        for g in day:
            for t in (g["home"], g["away"]):
                if g["id"] not in box:
                    continue
                for p in box[g["id"]].get(t, []):
                    if p["min"] > 0:
                        pl = norm(p["name"])
                        if last_team.get(pl) != t:
                            logs[pl] = deque(maxlen=window)  # new team: start his record here
                        logs.setdefault(pl, deque(maxlen=window)).append((p["min"], p["gmsc"]))
                        last_team[pl] = t
                team_games.setdefault(t, []).append(g["id"])


def add_lineups(games, recent_games=3, window=10, use_report=True):
    """For each team-game: the players EXPECTED to play, known the night before, with expected minutes,
    and the players who ACTUALLY played (box score), which the model only learns from afterwards.
    Expected: played in one of the team's last 3 games this season and still with the team; minus
    anyone listed Out or Doubtful on the night-before report; Questionable players get 70% of their
    minutes. Expected minutes are each player's recent average, scaled to 240 for the team."""
    for g in games:
        g["home_exp"] = g["away_exp"] = g["home_act"] = g["away_act"] = ()
    if not os.path.exists("data/boxscores.json"):
        return
    box = json.load(open("data/boxscores.json"))
    inj = json.load(open("data/injuries.json")) if use_report and os.path.exists("data/injuries.json") else {}
    mins, last_team, team_games, season = {}, {}, {}, None
    cut = {"Out": 0.0, "Doubtful": 0.0, "Questionable": 0.7}
    for day in game_days(games):
        if day[0]["season"] != season:
            season, team_games = day[0]["season"], {}
        for g in day:
            listed = inj.get(g["id"]) or {}
            for side in ("home", "away"):
                t = g[side]
                status = {norm(n): s for n, s in listed.get(t, {}).items()}
                pool = {norm(p["name"]) for gid in team_games.get(t, [])[-recent_games:]
                        for p in box.get(gid, {}).get(t, []) if p["min"] > 0}
                exp = []
                for pl in pool:
                    if last_team.get(pl) != t or not mins.get(pl):
                        continue
                    m = st.mean(mins[pl]) * cut.get(status.get(pl), 1.0)
                    if m > 0:
                        exp.append((pl, m))
                total = sum(m for _, m in exp)
                g[side + "_exp"] = tuple((pl, m * 240 / total) for pl, m in exp) if total >= 150 else ()
                g[side + "_act"] = tuple((norm(p["name"]), p["min"]) for p in box.get(g["id"], {}).get(t, [])
                                         if p["min"] > 0)
        for g in day:  # learn the day's minutes only after it is priced
            for t in (g["home"], g["away"]):
                for p in box.get(g["id"], {}).get(t, []):
                    if p["min"] > 0:
                        pl = norm(p["name"])
                        if last_team.get(pl) != t:
                            mins[pl] = deque(maxlen=window)
                        mins.setdefault(pl, deque(maxlen=window)).append(p["min"])
                        last_team[pl] = t
                if g["id"] in box:
                    team_games.setdefault(t, []).append(g["id"])


# ---------- model ----------

def run(games, k=0.03, hca=2.5, carry=0.7, k_market=0.0, b2b=0.0, inj=0.0,
        ret=0.0, three=0.0, rest=0.0, tz=0.0, mov_cap=None, early=0.0, home_own=0.0, home_n0=100, roster=0.0,
        p_w=0.0, p_k=0.0, p_mkt=0.0, p_carry=0.8, trace=None):
    """Walk forward one day at a time. Returns each game's predicted home margin."""
    rating, season, preds, played = {}, None, [], {}
    home_sum, home_n = {}, {}  # each team's leftover error in its own home games (all seasons so far)
    prate = {}  # player -> points per 48 minutes he adds to his team's margin
    for day in game_days(games):
        if day[0]["season"] != season:  # new season: ratings shrink toward average
            season, played = day[0]["season"], {}
            rating = {t: r * carry for t, r in rating.items()}
            prate = {pl: r * p_carry for pl, r in prate.items()}
        day_preds = []
        for g in day:  # price the whole day first
            p = rating.get(g["home"], 0.0) - rating.get(g["away"], 0.0) + (0 if g["neutral"] else hca)
            if home_own and not g["neutral"]:  # this team's own home edge, pulled toward the league's
                p += home_own * home_sum.get(g["home"], 0.0) / (home_n.get(g["home"], 0) + home_n0)
            p += b2b * (g["away_b2b"] - g["home_b2b"])
            p += inj * (g["away_miss"] - g["home_miss"])
            if g["home_roster"] and g["away_roster"]:  # both rosters known
                p += roster * (g["home_roster"] - g["away_roster"])
            if p_w and g["home_exp"] and g["away_exp"]:  # player ratings, from expected lineups
                p += p_w * (sum(prate.get(pl, 0.0) * m for pl, m in g["home_exp"])
                            - sum(prate.get(pl, 0.0) * m for pl, m in g["away_exp"])) / 48
            p += ret * (g["home_back"] - g["away_back"])
            p += three * (g["away_3in4"] - g["home_3in4"])
            p += rest * (g["home_rest"] - g["away_rest"])
            p += tz * (g["away_tz"] - g["home_tz"])
            if trace is not None:  # "show your working" for one game, used by explain.py
                lineup = lambda side: sorted(((pl, m, prate.get(pl, 0.0)) for pl, m in g[side + "_exp"]),
                                             key=lambda x: -x[1])
                both = g["home_exp"] and g["away_exp"]
                trace[g["id"]] = {
                    "team": (rating.get(g["home"], 0.0), rating.get(g["away"], 0.0)),
                    "home_court": 0 if g["neutral"] else hca,
                    "b2b": b2b * (g["away_b2b"] - g["home_b2b"]),
                    "injury": inj * (g["away_miss"] - g["home_miss"]),
                    "box_players": roster * (g["home_roster"] - g["away_roster"]) if g["home_roster"] and g["away_roster"] else 0.0,
                    "players": p_w * (sum(r * m for _, m, r in lineup("home")) - sum(r * m for _, m, r in lineup("away"))) / 48 if both else 0.0,
                    "lineups": (lineup("home"), lineup("away")), "total": p}
            day_preds.append(p)
        preds.extend(day_preds)
        for g, p in zip(day, day_preds):  # then learn from it
            margin = g["margin"] if mov_cap is None else max(-mov_cap, min(mov_cap, g["margin"]))
            err = margin - p
            n = min(played.get(g["home"], 0), played.get(g["away"], 0))
            kk = k * (1 + early * max(0, 20 - n) / 20)  # learn faster while ratings are least certain
            rating[g["home"]] = rating.get(g["home"], 0.0) + kk * err
            rating[g["away"]] = rating.get(g["away"], 0.0) - kk * err
            played[g["home"]], played[g["away"]] = played.get(g["home"], 0) + 1, played.get(g["away"], 0) + 1
            if not g["neutral"]:
                home_sum[g["home"]] = home_sum.get(g["home"], 0.0) + (g["margin"] - p)
                home_n[g["home"]] = home_n.get(g["home"], 0) + 1
            if p_k or p_mkt:  # share the miss among the players who actually played, by minutes
                m_err = (-g["learn_close"] - p) if (p_mkt and g["learn_close"] is not None) else 0.0
                step = p_k * err + p_mkt * m_err
                for pl, m in g["home_act"]:
                    prate[pl] = prate.get(pl, 0.0) + step * m / 48
                for pl, m in g["away_act"]:
                    prate[pl] = prate.get(pl, 0.0) - step * m / 48
            if k_market and g["learn_close"] is not None:
                m_err = -g["learn_close"] - p
                rating[g["home"]] += k_market * m_err
                rating[g["away"]] -= k_market * m_err
    return preds


def gaps(games, preds, season, line="close", only=None):
    return [abs(p + g[line]) for g, p in zip(games, preds)
            if g["season"] == season and g[line] is not None and (only is None or only(g))]


def tune(games, grid, season=None):
    season = season or TUNE
    return min(((st.mean(gaps(games, run(games, **p), season)), p) for p in grid), key=lambda x: x[0])


def tuned_models(games, season=None):
    """Each step adds one idea; every setting is chosen on the tuning season only."""
    grid = [dict(k=k, hca=h, carry=c) for k in (0.01, 0.02, 0.03, 0.04, 0.05, 0.07)
            for h in (1.5, 2.0, 2.5, 3.0, 3.5) for c in (0.4, 0.55, 0.7, 0.85)]
    _, base = tune(games, grid, season)
    _, mkt = tune(games, [dict(base, k_market=x) for x in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4)], season)
    _, rest = tune(games, [dict(mkt, b2b=x) for x in (0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)], season)
    _, injp = tune(games, [dict(rest, inj=x) for x in (0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)], season)
    _, plyr = tune(games, [dict(injp, roster=w, k=k) for w in (0.02, 0.03, 0.05, 0.07, 0.1)
                           for k in (0.015, 0.02, 0.025, 0.03)], season)
    # Full player ratings: each player learns how much he adds per 48 minutes, mostly from closing
    # lines; team strength comes from the expected lineup. Grid around the values experiment_players.py
    # found on 2024-25 (confirmed there to depend on the injury report; see DETAILS).
    _, full = tune(games, [dict(plyr, p_w=0.75, p_carry=1.0, p_k=0.001, p_mkt=pm, k_market=km, k=k, inj=i)
                           for pm in (0.015, 0.02, 0.025) for km in (0.1, 0.15) for k in (0.01, 0.02)
                           for i in (0.1, 0.15)], season)
    return {"baseline": base, "+ past closes": mkt, "+ back-to-backs": rest, "+ injuries": injp,
            "+ box-score players": plyr, "+ player ratings": full}


def bootstrap(a, b, n=10000, seed=7):
    """Average of (a - b) over games, with a 95% range from resampling the games."""
    rnd, d = random.Random(seed), [x - y for x, y in zip(a, b)]
    means = sorted(st.mean(rnd.choices(d, k=len(d))) for _ in range(n))
    return st.mean(d), means[int(0.025 * n)], means[int(0.975 * n)]


def report(games, models, season, only=None, label=""):
    preds = {n: run(games, **p) for n, p in models.items()}
    names = list(models)
    for line in ("close", "open"):
        g = {n: gaps(games, pr, season, line, only) for n, pr in preds.items()}
        books = sorted({x["key_book"] for x in games if x["season"] == season and x["key_book"]})
        print(f"\n{season}{label} vs the {' / '.join(books)} {line.upper()} ({len(g['baseline'])} games): average points off")
        for n in names:
            print(f"  {n:16} {st.mean(g[n]):.2f}")
        for a, b in zip(names, names[1:]):
            m, lo, hi = bootstrap(g[a], g[b])
            verdict = "real" if lo > 0 else ("worse" if hi < 0 else "could be noise")
            print(f"  {b} vs {a}: {m:+.2f} points, 95% range {lo:+.2f} to {hi:+.2f} ({verdict})")
    best = preds[names[-1]]
    rows = [(abs(g["margin"] - p), abs(g["margin"] + g["close"])) for g, p in zip(games, best)
            if g["season"] == season and g["close"] is not None and (only is None or only(g))]
    m, lo, hi = bootstrap([r[0] for r in rows], [r[1] for r in rows])
    print(f"\n  vs the real final margin: model misses by {st.mean(r[0] for r in rows):.2f}, "
          f"the close by {st.mean(r[1] for r in rows):.2f} (close better by {m:.2f}, {lo:.2f} to {hi:.2f})")
    return preds


def win_probability(games, preds, season):
    """Margin -> win probability with a bell curve whose width is measured on earlier seasons."""
    sigma = st.pstdev([g["margin"] - p for g, p in zip(games, preds) if g["season"] < TUNE])
    rows = [(0.5 * (1 + math.erf(p / (sigma * math.sqrt(2)))), g["close_prob"], g["margin"] > 0)
            for g, p in zip(games, preds) if g["season"] == season and g["close_prob"] is not None]
    ll = lambda p, w: -math.log(min(max(p if w else 1 - p, 1e-6), 1))
    ours, book = [ll(p, w) for p, _, w in rows], [ll(b, w) for _, b, w in rows]
    m, lo, hi = bootstrap(ours, book)
    print(f"\n{season} win probability ({len(rows)} games, bell-curve width {sigma:.1f} points)")
    print(f"  average gap to the no-vig close: {st.mean(abs(p - b) for p, b, _ in rows) * 100:.1f} points")
    print(f"  log loss: model {st.mean(ours):.4f}, closing price {st.mean(book):.4f}, coin flip {math.log(2):.4f}"
          f"  (close better by {m:.4f}, {lo:.4f} to {hi:.4f})")
    for lo_b in (0.0, 0.2, 0.4, 0.6, 0.8):
        b = [w for p, _, w in rows if lo_b <= p < lo_b + 0.2]
        if b:
            print(f"    model said {lo_b:.0%} to {lo_b + 0.2:.0%}: home won {st.mean(b):.0%} of {len(b)}")


if __name__ == "__main__":
    import sys
    season = TEST if "--test" in sys.argv else TUNE
    games = load()
    models = tuned_models(games)
    for n, p in models.items():
        print(f"{n:16} {p}")
    preds = report(games, models, season)
    win_probability(games, preds[list(models)[-1]], season)
    if season == TEST:  # the injury step can only be judged where the night-before reports exist
        print("\n" + "=" * 70)
        report(games, models, season, only=lambda g: g["has_report"], label=" (games with an injury report)")
