"""Everything the model knows about a game by the end of the day before it.

load() reads the downloaded files (see the fetch_*.py scripts) and adds, to every game:
  close, open        the answer key: one book's pre-game closing (and opening) spread for the home
                     team, negative = home favoured
  close_prob         that book's no-vig closing win probability for the home team
  home_b2b, away_b2b second night of a back-to-back
  home_miss, ...     rotation value missing per the night-before injury report
  home_roster, ...   strength of the players expected to be available, from their box scores
  home_exp, ...      expected lineup: (player, expected minutes)
  home_act, ...      who actually played (box score); the model only LEARNS from this after the game

A recurring rule: a day's games are processed first, and only afterwards is anything from that day
(results, box scores, lines) added to what is known. That is what keeps game-day information out.
"""
import json
import os
import statistics as st
import unicodedata
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
TUNE, TEST = "2024-25", "2025-26"   # settings are chosen on TUNE; TEST is graded once
MAX_SPREAD = 30                     # sanity rule: no NBA spread is bigger (ESPN once stored prices like -110)


# ---------- small helpers ----------

def local_day(g):
    """The game's calendar day in US Eastern time."""
    return datetime.fromisoformat(g["date"].replace("Z", "+00:00")).astimezone(ET).date()


def game_days(games):
    """Games grouped by day, in order. The model always handles a whole day at once."""
    days, key = [], None
    for g in games:
        d = local_day(g)
        if d != key:
            days.append([])
            key = d
        days[-1].append(g)
    return days


def clean(x):
    return x if x is not None and abs(x) <= MAX_SPREAD else None


def no_vig(home_odds, away_odds):
    """American moneyline odds -> the home team's win probability with the book's margin removed."""
    if not home_odds or not away_odds:
        return None
    prob = lambda o: -o / (-o + 100) if o < 0 else 100 / (o + 100)
    ph, pa = prob(home_odds), prob(away_odds)
    return ph / (ph + pa) if 1.0 < ph + pa < 1.15 else None  # real two-way markets add up to a bit over 100%


def norm(name):
    """Player names from different sources match: 'Nikola Jović' = 'Nikola Jovic', 'P.J.' = 'PJ'."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return " ".join("".join(c for c in name.lower() if c.isalpha() or c == " ").split())


# ---------- the answer key ----------

def key_book(season):
    """The book whose pre-game close each season is graded against, as recorded by ESPN.
    ESPN switched partners from ESPN BET to DraftKings during 2025-26."""
    return ("DraftKings", "ESPN BET") if season == "2025-26" else ("ESPN BET",)


def add_lines(games):
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
        if g["close"] is None:
            # Seasons before 2023-24 have no labelled pre-game close in ESPN's data. For the ten-season
            # test they use the best line ESPN has: Pinnacle (2015-16 only), else its consensus line,
            # else the median of the books it lists.
            pin = next((clean(r.get("spread")) for name, r in books.items()
                        if "pinnacle" in name.lower() and clean(r.get("spread")) is not None), None)
            cons = clean((books.get("consensus") or {}).get("spread"))
            others = [clean(r.get("spread")) for name, r in books.items()
                      if clean(r.get("spread")) is not None and name != "Opening"]
            for line, source in ((pin, "Pinnacle"), (cons, "ESPN consensus"),
                                 (st.median(others) if others else None, "median of books")):
                if line is not None:
                    g["close"], g["key_book"] = line, source
                    break


# ---------- the schedule ----------

def add_back_to_backs(games):
    """Is a team playing the second night of a back-to-back? The schedule is public months ahead."""
    last = {}
    for g in games:
        d = local_day(g)
        for side in ("home", "away"):
            t = g[side]
            g[side + "_b2b"] = t in last and (d - last[t]).days == 1
            last[t] = d


# ---------- players ----------
# A player's value = (Game Score per minute - a bench player's 0.15) x his usual minutes.
# Game Score is a standard one-number summary of a box-score line. Small samples are pulled
# toward a typical 0.25 per minute, as if he had already played 60 average minutes.

BENCH_RATE, MIN_MPG, MAX_MISS = 0.15, 16, 40.0
PRIOR_RATE, PRIOR_MIN = 0.25, 60


def rate(apps):
    """Game Score per minute from a list of (minutes, game score), pulled toward typical."""
    return (sum(x for _, x in apps) + PRIOR_RATE * PRIOR_MIN) / (sum(m for m, _ in apps) + PRIOR_MIN)


STATUS_WEIGHT = {"Out": 1.0, "Doubtful": 0.75, "Questionable": 0.3}


def add_injuries(games):
    """Rotation value each team is missing, from the NBA's injury report as it stood at the end of the
    evening before (see fetch_injuries.py). Only regulars count: 3+ of the team's last 10 games and
    16+ minutes a game, still with the team. Games with no report (g["has_report"] False) get zero."""
    for g in games:
        g["home_miss"] = g["away_miss"] = 0.0
        g["has_report"] = False
    box, inj = json.load(open("data/boxscores.json")), json.load(open("data/injuries.json"))
    recent, played, last_team = {}, {}, {}  # team -> last 10 game ids; player -> {id: (min, gmsc)}; player -> team
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
                    mpg = sum(m for m, _ in apps) / len(apps)
                    if mpg < MIN_MPG:
                        continue
                    miss += w * max(0.0, rate(apps) - BENCH_RATE) * mpg
                g[side + "_miss"] = min(miss, MAX_MISS)  # a whole rotation resting can't swamp the scale
        for g in day:  # only now does the day's box score become known
            for t in (g["home"], g["away"]):
                for p in box.get(g["id"], {}).get(t, []):
                    if p["min"] > 0:
                        played.setdefault(norm(p["name"]), {})[g["id"]] = (p["min"], p["gmsc"])
                        last_team[norm(p["name"])] = t
                recent.setdefault(t, deque(maxlen=10)).append(g["id"])


def add_roster(games, window=20, recent_games=3):
    """Strength of the players expected to be available: everyone who played in one of the team's
    last 3 games this season and is still with the team, valued over his last 20 games with it,
    with the team's minutes scaled to the 240 it actually plays."""
    for g in games:
        g["home_roster"] = g["away_roster"] = 0.0
    box = json.load(open("data/boxscores.json"))
    logs, last_team, team_games, season = {}, {}, {}, None
    for day in game_days(games):
        if day[0]["season"] != season:
            season, team_games = day[0]["season"], {}  # only this season's games say who is available
        for g in day:
            for side in ("home", "away"):
                t = g[side]
                available = {norm(p["name"]) for gid in team_games.get(t, [])[-recent_games:]
                             for p in box.get(gid, {}).get(t, []) if p["min"] > 0}
                players = []
                for pl in available:
                    if last_team.get(pl) != t or len(logs.get(pl, ())) < 3:
                        continue
                    players.append((rate(logs[pl]), sum(m for m, _ in logs[pl]) / len(logs[pl])))
                total_min = sum(m for _, m in players)
                scale = 240 / total_min if total_min > 240 else 1.0
                g[side + "_roster"] = sum((r - BENCH_RATE) * m * scale for r, m in players)
        for g in day:  # only now does the day's box score become known
            for t in (g["home"], g["away"]):
                if g["id"] not in box:
                    continue
                for p in box[g["id"]].get(t, []):
                    if p["min"] > 0:
                        pl = norm(p["name"])
                        if last_team.get(pl) != t:
                            logs[pl] = deque(maxlen=window)  # new team: his record starts here
                        logs.setdefault(pl, deque(maxlen=window)).append((p["min"], p["gmsc"]))
                        last_team[pl] = t
                team_games.setdefault(t, []).append(g["id"])


def add_lineups(games, recent_games=3, window=10, use_report=True):
    """Expected lineup the night before: recent players (one of the last 3 games, still with the team)
    minus anyone listed Out or Doubtful; Questionable players get 70% of their minutes. Minutes are
    each player's recent average, scaled to 240. Also records who actually played, for learning later."""
    for g in games:
        g["home_exp"] = g["away_exp"] = g["home_act"] = g["away_act"] = ()
    box = json.load(open("data/boxscores.json"))
    inj = json.load(open("data/injuries.json")) if use_report else {}
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
        for g in day:  # only now does the day's box score become known
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


# ---------- everything together ----------

def load():
    games = sorted((json.loads(l) for l in open("data/games.jsonl")), key=lambda g: g["date"])
    for g in games:
        g["margin"] = g["home_pts"] - g["away_pts"]
    add_lines(games)
    add_back_to_backs(games)
    add_injuries(games)
    add_roster(games)
    add_lineups(games)
    return games
