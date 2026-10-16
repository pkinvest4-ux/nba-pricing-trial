"""Which number best says how much a missing player matters? Run:  python3 player_values.py

The injury step values each missing regular by his Game Score per minute. This tries other ways:
  plus-minus     his plus-minus per minute over his last 40 games (ESPN box scores)
  points         his points per minute
  win shares     last season's win shares per 48 minutes (Basketball-Reference)
  BPM            last season's Box Plus/Minus (Basketball-Reference)
  game score + plus-minus   both together
Each is turned into the same units as Game Score, then its weight is chosen on 2024-25.

The rule, fixed before 2025-26 is graded: the best way on 2024-25 replaces Game Score only if its gain
over Game Score on 2024-25 is real (95% range above zero). 2025-26 is then graded once either way.
Plus-minus and points start in 2022-23, so every way uses Game Score before that.
"""
import json
import statistics as st
from collections import deque
from data import load, game_days, norm, rate, STATUS_WEIGHT, MIN_MPG, MAX_MISS, BENCH_RATE, TUNE, TEST
from model import run, gaps, tuned_models
from evaluate import bootstrap

FIRST = "2022-23"
PRIOR = {"plus-minus": (0.0, 400), "points": (0.45, 60)}  # (typical per-minute value, minutes it counts for)


def missing_values(games):
    """For every game and side, the regulars listed on the night-before report: (weight, minutes a game,
    his record). Built the same way as data.add_injuries, so only the value per minute changes."""
    box, inj = json.load(open("data/boxscores.json")), json.load(open("data/injuries.json"))
    pm = json.load(open("data/plusminus.json"))
    recent, played, history, last_team, out = {}, {}, {}, {}, {}
    for day in game_days(games):
        for g in day:
            listed = inj.get(g["id"]) or {}
            for side in ("home", "away"):
                t, rows = g[side], []
                for player, status in listed.get(t, {}).items():
                    w, pl = STATUS_WEIGHT.get(status, 0.0), norm(player)
                    if not w or last_team.get(pl) != t:
                        continue
                    apps = [played[pl][gid] for gid in recent.get(t, ()) if gid in played.get(pl, {})]
                    if len(apps) < 3:
                        continue
                    mpg = sum(m for m, _ in apps) / len(apps)
                    if mpg >= MIN_MPG:
                        rows.append((w, mpg, pl, rate(apps) - BENCH_RATE, tuple(history.get(pl, ()))))
                out[g["id"], side] = rows
        for g in day:
            for t in (g["home"], g["away"]):
                extra = {norm(n): v for n, v in pm.get(g["id"], {}).get(t, {}).items()}
                for p in box.get(g["id"], {}).get(t, []):
                    if p["min"] > 0:
                        pl = norm(p["name"])
                        played.setdefault(pl, {})[g["id"]] = (p["min"], p["gmsc"])
                        last_team[pl] = t
                        if pl in extra:
                            history.setdefault(pl, deque(maxlen=40)).append(extra[pl])
                recent.setdefault(t, deque(maxlen=10)).append(g["id"])
    return out


def per_minute(way, pl, gmsc, hist, season, ws, bench):
    """A missing regular's value per minute above a bench player, under each way of valuing him."""
    if way == "game score":
        return gmsc
    if way in PRIOR:
        typ, weight = PRIOR[way]
        i = 2 if way == "plus-minus" else 1
        r = (sum(h[i] for h in hist) + typ * weight) / (sum(h[0] for h in hist) + weight)
        return r - bench
    last = ws.get(prev_season(season), {}).get(pl)
    if last is None or last["min"] < 250:  # rookies and barely-played: a bench player
        return 0.0
    return (last["ws48"] - bench) / 48 if way == "win shares" else (last["bpm"] - bench) / 48


def prev_season(s):
    a = int(s[:4]) - 1
    return f"{a}-{str(a + 1)[2:]}"


def set_miss(games, rows, way, ws, bench=0.0, blend=0.0, scale=None):
    """Write each game's missing value under `way` into home_miss / away_miss, in Game Score units."""
    vals = {}
    for g in games:
        for side in ("home", "away"):
            r = rows.get((g["id"], side), [])
            gs = sum(w * max(0.0, v) * mpg for w, mpg, _, v, _ in r)
            if g["season"] < FIRST or way == "game score":
                vals[g["id"], side] = (gs, None)
                continue
            alt = sum(w * max(0.0, per_minute(way.replace("game score + ", ""), pl, v, h, g["season"], ws, bench)) * mpg
                      for w, mpg, pl, v, h in r)
            vals[g["id"], side] = (gs, alt)
    if scale is None:  # one unit conversion, measured before the tuning season
        a = [x[1] for k, x in vals.items() if x[1] and next_season_ok(k, games)]
        b = [x[0] for k, x in vals.items() if x[1] and next_season_ok(k, games)]
        scale = st.mean(b) / st.mean(a) if a and st.mean(a) else 0.0
    for g in games:
        for side in ("home", "away"):
            gs, alt = vals[g["id"], side]
            m = gs if alt is None else (gs + blend * alt * scale if way.startswith("game score +") else alt * scale)
            g[side + "_miss"] = min(m, MAX_MISS)
    return scale


_SEASON = {}


def next_season_ok(key, games):
    if not _SEASON:
        _SEASON.update({g["id"]: g["season"] for g in games})
    return FIRST <= _SEASON[key[0]] < TUNE


if __name__ == "__main__":
    games = load()
    ws = {s: {norm(n): v for n, v in p.items()} for s, p in json.load(open("data/winshares.json")).items()}
    rows = missing_values(games)
    final = tuned_models(games)["+ player ratings"]
    ways = {"game score": [dict()],
            "plus-minus": [dict(bench=b) for b in (-0.1, -0.05, 0.0)],
            "points": [dict(bench=b) for b in (0.2, 0.3, 0.4)],
            "win shares": [dict(bench=b) for b in (0.0, 0.05, 0.08)],
            "BPM": [dict(bench=b) for b in (-4.0, -2.0, 0.0)],
            "game score + plus-minus": [dict(bench=b, blend=x) for b in (-0.05, 0.0) for x in (0.25, 0.5, 1.0)]}
    best = {}
    for way, opts in ways.items():
        results = []
        for o in opts:
            for inj in (0.05, 0.1, 0.15, 0.2):
                set_miss(games, rows, way, ws, **o)
                p = run(games, **dict(final, inj=inj))
                results.append((st.mean(gaps(games, p, TUNE)), o, inj, p))
        best[way] = min(results, key=lambda r: r[0])
        print(f"{way:26} 2024-25: {best[way][0]:.3f}   {best[way][1]} inj {best[way][2]}")

    base = gaps(games, best["game score"][3], TUNE)
    winner = min((w for w in best if w != "game score"), key=lambda w: best[w][0])
    m, lo, hi = bootstrap(base, gaps(games, best[winner][3], TUNE))
    use = winner if lo > 0 else "game score"
    print(f"\nbest other way on 2024-25: {winner}, {m:+.3f} vs game score ({lo:+.3f} to {hi:+.3f})  ->  using: {use}")

    print(f"\n{TEST}, graded once:")
    for way in dict.fromkeys(["game score", winner]):
        _, o, inj, _ = best[way]
        set_miss(games, rows, way, ws, **o)
        print(f"  {way:26} {st.mean(gaps(games, run(games, **dict(final, inj=inj)), TEST)):.3f}")
