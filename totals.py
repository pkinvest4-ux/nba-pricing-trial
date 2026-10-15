"""Over/under line-making: price each game's total points the night before, graded against the closing
total. Same rules as the spread model: walk forward one day at a time, price a day before learning
from it, choose every setting on 2024-25, and grade 2025-26 once.

How it works, in plain words:
- Each team has an offence rating (points it scores above the league average) and a defence rating
  (points it allows above average). The league average drifts as scoring changes.
- Expected home points = league average + home offence + away defence + half the home edge,
  and the same for the away team. The predicted total is the sum.
- After each day, ratings move toward the actual points and, as an improvement, toward what the
  closing total said. Then back-to-backs and injury-report absences adjust each team's points.
"""
import json, statistics as st, sys
import model

MIN_TOTAL, MAX_TOTAL = 170, 280  # sanity rule: ESPN stored prices like -110 in this field in 2022-23


def ok(x):
    return x if x is not None and MIN_TOTAL <= x <= MAX_TOTAL else None


def add_totals(games):
    odds = json.load(open("data/espn_odds.json"))
    for g in games:
        books = odds.get(g["id"], {})
        g["close_total"] = g["open_total"] = None
        for b in model.key_book(g["season"]):
            rec = books.get(b) or {}
            if ok(rec.get("close_total")) is not None:
                g["close_total"], g["open_total"] = ok(rec["close_total"]), ok(rec.get("open_total"))
                break
        g["learn_total"] = g["close_total"]
        if g["learn_total"] is None:  # older seasons: median of what ESPN lists
            vals = [ok(r.get("total")) for r in books.values() if ok(r.get("total")) is not None]
            g["learn_total"] = st.median(vals) if vals else None
        g["total"] = g["home_pts"] + g["away_pts"]


def run(games, k=0.03, carry=0.6, k_avg=0.01, k_market=0.0, b2b=0.0, inj=0.0, roster=0.0):
    off, dfn, avg, season, preds = {}, {}, 110.0, None, []
    for day in model.game_days(games):
        if day[0]["season"] != season:
            season = day[0]["season"]
            off = {t: r * carry for t, r in off.items()}
            dfn = {t: r * carry for t, r in dfn.items()}
        day_preds = []
        for g in day:  # price the whole day first
            h, a = g["home"], g["away"]
            ph = avg + off.get(h, 0.0) + dfn.get(a, 0.0)
            pa = avg + off.get(a, 0.0) + dfn.get(h, 0.0)
            ph += b2b * g["home_b2b"] + inj * g["home_miss"] / 10
            pa += b2b * g["away_b2b"] + inj * g["away_miss"] / 10
            if g["home_roster"] and g["away_roster"]:
                ph += roster * (g["home_roster"] - 50) / 10
                pa += roster * (g["away_roster"] - 50) / 10
            day_preds.append((ph, pa))
        preds.extend(ph + pa for ph, pa in day_preds)
        for g, (ph, pa) in zip(day, day_preds):  # then learn from it
            h, a = g["home"], g["away"]
            eh, ea = g["home_pts"] - ph, g["away_pts"] - pa
            off[h], dfn[a] = off.get(h, 0.0) + k * eh, dfn.get(a, 0.0) + k * eh
            off[a], dfn[h] = off.get(a, 0.0) + k * ea, dfn.get(h, 0.0) + k * ea
            avg += k_avg * (eh + ea) / 2
            if k_market and g["learn_total"] is not None:
                m = (g["learn_total"] - ph - pa) / 4
                for d, t in ((off, h), (off, a), (dfn, h), (dfn, a)):
                    d[t] = d.get(t, 0.0) + k_market * m
    return preds


def gaps(games, preds, season, line="close_total", only=None):
    return [abs(p - g[line]) for g, p in zip(games, preds)
            if g["season"] == season and g[line] is not None and (only is None or only(g))]


def tune(games, grid):
    return min(((st.mean(gaps(games, run(games, **p), model.TUNE)), p) for p in grid), key=lambda x: x[0])


def tuned_models(games):
    """Each step adds one idea; every setting is chosen on 2024-25. Player ratings were tried here too and
    added nothing for totals (2024-25: +0.00, -0.01 to +0.02), so the totals model leaves them out."""
    _, base = tune(games, [dict(k=k, carry=c, k_avg=a) for k in (0.03, 0.05, 0.07, 0.1, 0.14)
                           for c in (0.3, 0.5, 0.7) for a in (0.002, 0.005, 0.01)])
    _, mkt = tune(games, [dict(base, k_market=x) for x in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0)])
    _, rest = tune(games, [dict(mkt, b2b=x) for x in (-3, -2, -1.5, -1, -0.5, 0, 0.5, 1)])
    _, injp = tune(games, [dict(rest, inj=x) for x in (-3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5)])
    return {"baseline": base, "+ past closes": mkt, "+ back-to-backs": rest, "+ injuries": injp}


if __name__ == "__main__":
    season = model.TEST if "--test" in sys.argv else model.TUNE
    games = model.load()
    add_totals(games)
    models = tuned_models(games)
    for n, p in models.items():
        print(f"{n:16} {p}")
    preds = {n: run(games, **p) for n, p in models.items()}
    names = list(models)
    for line in ("close_total", "open_total"):
        g = {n: gaps(games, pr, season, line) for n, pr in preds.items()}
        print(f"\n{season} TOTALS vs the {line.replace('_', ' ').upper()} ({len(g['baseline'])} games): average points off")
        for n in names:
            print(f"  {n:16} {st.mean(g[n]):.2f}")
        for a, b in zip(names, names[1:]):
            m, lo, hi = model.bootstrap(g[a], g[b])
            verdict = "real" if lo > 0 else ("worse" if hi < 0 else "could be noise")
            print(f"  {b} vs {a}: {m:+.2f} points, 95% range {lo:+.2f} to {hi:+.2f} ({verdict})")
    best = preds[names[-1]]
    rows = [(abs(g["total"] - p), abs(g["total"] - g["close_total"])) for g, p in zip(games, best)
            if g["season"] == season and g["close_total"] is not None]
    m, lo, hi = model.bootstrap([r[0] for r in rows], [r[1] for r in rows])
    print(f"\n  vs the real total: model misses by {st.mean(r[0] for r in rows):.2f}, the close by "
          f"{st.mean(r[1] for r in rows):.2f} (close better by {m:.2f}, {lo:.2f} to {hi:.2f})")
