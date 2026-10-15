"""How well does 'regular sat out the previous game' match the official injury report?
Uses 2024-25, the season where the evening-before reports are complete."""
import json, model

games = model.load()
inj = json.load(open("data/injuries.json"))
both = proxy_only = report_only = 0
for g in games:
    if g["season"] != "2024-25":
        continue
    for side in ("home", "away"):
        absent = set(g[side + "_absent"])
        listed = {model.norm(n) for n, s in inj.get(g["id"], {}).get(g[side], {}).items() if s in ("Out", "Doubtful")}
        # only compare players our measure considers regulars, i.e. those it could have flagged
        both += len(absent & listed)
        proxy_only += len(absent - listed)
recall_side = 0
print(f"regulars flagged as sat-out-last-game: {both + proxy_only}")
print(f"  also listed Out/Doubtful on the evening-before report: {both / (both + proxy_only):.0%}")
