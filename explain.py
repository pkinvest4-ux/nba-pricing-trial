"""Show how the final model priced one game, piece by piece.
Usage: python3 explain.py AWAY HOME YYYY-MM-DD      e.g.  python3 explain.py WSH DET 2025-11-10"""
import sys
from data import load, local_day
from model import run, tuned_models

away, home, day = sys.argv[1], sys.argv[2], sys.argv[3]
games = load()
trace = {}
run(games, **tuned_models(games)["+ player ratings"], trace=trace)
g = next(g for g in games if g["home"] == home and g["away"] == away and local_day(g).isoformat() == day)
t = trace[g["id"]]
tired = ("home tired" if g["home_b2b"] else "") + (" away tired" if g["away_b2b"] else "") or "neither"
print(f"\n{away} at {home}, {day}  (positive = {home} favoured)\n")
print(f"  team ratings          {home} {t['ratings'][0]:+.1f}, {away} {t['ratings'][1]:+.1f}  ->  {t['team']:+.1f}")
print(f"  home court                                 {t['home_court']:+.1f}")
print(f"  back-to-back          {tired:<26} {t['b2b']:+.1f}")
print(f"  injury report         {home} missing {g['home_miss']:.1f}, {away} missing {g['away_miss']:.1f}  ->  {t['injury']:+.1f}")
print(f"  box-score players                          {t['box_players']:+.1f}")
print(f"  player ratings (expected lineups)          {t['players']:+.1f}")
print(f"  {'-' * 50}")
print(f"  MODEL: {home} by {t['total']:+.1f}   CLOSE: {home} by {-g['close']:+.1f} ({g['key_book']})   RESULT: {home} by {g['margin']:+d}")
for team, lineup in ((home, t["lineups"][0]), (away, t["lineups"][1])):
    print(f"\n  {team} expected lineup (minutes, points per 48 he adds):")
    for pl, m, r in lineup[:9]:
        print(f"    {pl.title():24} {m:4.0f} min   {r:+.1f}")
