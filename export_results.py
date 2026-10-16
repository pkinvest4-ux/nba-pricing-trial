"""Write the results to spreadsheets (open them in Excel, Numbers or Google Sheets). Run:  python3 export_results.py

results_by_game.csv   every game of 2024-25 (tuning) and 2025-26 (test): how the spread was built,
                      the model's number next to the close and the result, and the same for the total.
results_summary.csv   the headline numbers for each season.
Positive numbers mean the home team is favoured, or wins by that much.
"""
import csv
import statistics as st
from data import load, local_day, TUNE, TEST
from model import run, tuned_models
import totals

games = load()
totals.add_totals(games)
trace = {}
spread = run(games, **tuned_models(games)["+ player ratings"], trace=trace)
total = totals.run(games, **totals.tuned_models(games)["+ injuries"])

rows = []
for g, p, t in zip(games, spread, total):
    if g["season"] not in (TUNE, TEST) or g["close"] is None:
        continue
    parts = trace[g["id"]]
    close = -g["close"]  # the close is quoted as the home spread, so -5.5 means home by 5.5
    row = {
        "season": g["season"], "date": local_day(g).isoformat(), "away": g["away"], "home": g["home"],
        "book": g["key_book"], "injury report": "yes" if g["has_report"] else "no",
        "team ratings": parts["team"], "home court": parts["home_court"], "back-to-back": parts["b2b"],
        "injuries": parts["injury"], "box-score players": parts["box_players"], "player ratings": parts["players"],
        "model: home by": p, "close: home by": close, "result: home by": g["margin"],
        "model minus close": p - close, "points off the close": abs(p - close),
        "model miss vs result": abs(g["margin"] - p), "close miss vs result": abs(g["margin"] - close),
        "closer to result": "model" if abs(g["margin"] - p) < abs(g["margin"] - close) else
                            "close" if abs(g["margin"] - p) > abs(g["margin"] - close) else "tie",
        "model total": t, "close total": g["close_total"], "actual total": g["total"],
        "total points off the close": abs(t - g["close_total"]) if g["close_total"] is not None else None,
    }
    rows.append(row)

with open("results_by_game.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows({k: round(v, 1) if isinstance(v, float) else v for k, v in r.items()} for r in rows)

with open("results_summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["season", "games", "spread: avg points off the close", "within 1 point", "within 2 points",
                "4+ points off", "avg lean (model minus close)", "model higher on home team",
                "model miss vs result", "close miss vs result", "model closer to result",
                "total: avg points off the close"])
    for season in (TUNE, TEST):
        s = [r for r in rows if r["season"] == season]
        off = [r["points off the close"] for r in s]
        tot = [r["total points off the close"] for r in s if r["total points off the close"] is not None]
        pct = lambda xs: f"{100 * sum(xs) / len(xs):.0f}%"
        w.writerow([season + (" (tuning)" if season == TUNE else " (test)"), len(s), f"{st.mean(off):.2f}",
                    pct([x <= 1 for x in off]), pct([x <= 2 for x in off]), pct([x >= 4 for x in off]),
                    f"{st.mean(r['model minus close'] for r in s):+.2f}", pct([r["model minus close"] > 0 for r in s]),
                    f"{st.mean(r['model miss vs result'] for r in s):.2f}",
                    f"{st.mean(r['close miss vs result'] for r in s):.2f}",
                    pct([r["closer to result"] == "model" for r in s]), f"{st.mean(tot):.2f}"])

print(f"wrote results_by_game.csv ({len(rows)} games) and results_summary.csv")
