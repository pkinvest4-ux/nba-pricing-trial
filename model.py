"""Price NBA games using only what was known by the end of the day before, and grade the price
against the closing line.

How it works, in plain words:
- Every team has a rating in points. Predicted home margin = home rating - away rating
  + home-court advantage, plus two adjustments known the night before:
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
        # What the model may LEARN from once a game is over: the key book's close, or for older
        # seasons without one, ESPN's consensus or the median of the books it lists.
        g["learn_close"] = g["close"]
        if g["learn_close"] is None:
            cons = clean((books.get("consensus") or {}).get("spread"))
            others = [clean(r.get("spread")) for r in books.values() if clean(r.get("spread")) is not None]
            g["learn_close"] = cons if cons is not None else (st.median(others) if others else None)
        g["margin"] = g["home_pts"] - g["away_pts"]
    for season in (TUNE, TEST):
        sg = [g for g in games if g["season"] == season]
        print(f"{season}: graded close for {sum(g['close'] is not None for g in sg)} of {len(sg)} games "
              f"({', '.join(b + ' ' + str(sum(g['key_book'] == b for g in sg)) for b in key_book(season))})")
    add_rest(games)
    add_injuries(games)
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


def add_rest(games):
    """Second night of a back-to-back. The schedule is public months ahead."""
    last = {}
    for g in games:
        d = local_day(g)
        for side in ("home", "away"):
            g[side + "_b2b"] = g[side] in last and (d - last[g[side]]).days == 1
            last[g[side]] = d


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
        g["has_report"] = False
    if not (os.path.exists("data/boxscores.json") and os.path.exists("data/injuries.json")):
        print("no injury data yet")
        return
    box, inj = json.load(open("data/boxscores.json")), json.load(open("data/injuries.json"))
    recent, played, last_team = {}, {}, {}  # team -> last 10 ids; player -> {id: (min, gmsc)}; player -> team
    for day in game_days(games):
        for g in day:
            listed = inj.get(g["id"])
            g["has_report"] = listed is not None
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
                        played.setdefault(norm(p["name"]), {})[g["id"]] = (p["min"], p["gmsc"])
                        last_team[norm(p["name"])] = t
                recent.setdefault(t, deque(maxlen=10)).append(g["id"])


# ---------- model ----------

def run(games, k=0.03, hca=2.5, carry=0.7, k_market=0.0, b2b=0.0, inj=0.0):
    """Walk forward one day at a time. Returns each game's predicted home margin."""
    rating, season, preds = {}, None, []
    for day in game_days(games):
        if day[0]["season"] != season:  # new season: ratings shrink toward average
            season = day[0]["season"]
            rating = {t: r * carry for t, r in rating.items()}
        day_preds = []
        for g in day:  # price the whole day first
            p = rating.get(g["home"], 0.0) - rating.get(g["away"], 0.0) + (0 if g["neutral"] else hca)
            p += b2b * (g["away_b2b"] - g["home_b2b"])
            p += inj * (g["away_miss"] - g["home_miss"])
            day_preds.append(p)
        preds.extend(day_preds)
        for g, p in zip(day, day_preds):  # then learn from it
            err = g["margin"] - p
            rating[g["home"]] = rating.get(g["home"], 0.0) + k * err
            rating[g["away"]] = rating.get(g["away"], 0.0) - k * err
            if k_market and g["learn_close"] is not None:
                m_err = -g["learn_close"] - p
                rating[g["home"]] += k_market * m_err
                rating[g["away"]] -= k_market * m_err
    return preds


def gaps(games, preds, season, line="close", only=None):
    return [abs(p + g[line]) for g, p in zip(games, preds)
            if g["season"] == season and g[line] is not None and (only is None or only(g))]


def tune(games, grid):
    return min(((st.mean(gaps(games, run(games, **p), TUNE)), p) for p in grid), key=lambda x: x[0])


def tuned_models(games):
    """Each step adds one idea; every setting is chosen on the tuning season only."""
    grid = [dict(k=k, hca=h, carry=c) for k in (0.01, 0.02, 0.03, 0.04, 0.05, 0.07)
            for h in (1.5, 2.0, 2.5, 3.0, 3.5) for c in (0.4, 0.55, 0.7, 0.85)]
    _, base = tune(games, grid)
    _, mkt = tune(games, [dict(base, k_market=x) for x in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4)])
    _, rest = tune(games, [dict(mkt, b2b=x) for x in (0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)])
    _, injp = tune(games, [dict(rest, inj=x) for x in (0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)])
    return {"baseline": base, "+ past closes": mkt, "+ back-to-backs": rest, "+ injuries": injp}


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
    print(f"  average gap to the consensus no-vig close: {st.mean(abs(p - b) for p, b, _ in rows) * 100:.1f} points")
    print(f"  log loss: model {st.mean(ours):.4f}, consensus close {st.mean(book):.4f}, coin flip {math.log(2):.4f}"
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
