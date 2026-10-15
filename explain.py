"""Show how the final model priced one game: python3 explain.py AWAY HOME YYYY-MM-DD"""
import sys
import model

away, home, day = sys.argv[1], sys.argv[2], sys.argv[3]
games = model.load()
params = model.tuned_models(games)["+ player ratings"]
trace = {}
model.run(games, **params, trace=trace)
g = next(g for g in games if g["home"] == home and g["away"] == away and model.local_day(g).isoformat() == day)
t = trace[g["id"]]
print(f"\n{away} at {home}, {day}  (positive = {home} favoured)\n")
print(f"  team ratings          {home} {t['team'][0]:+.1f}, {away} {t['team'][1]:+.1f}  ->  {t['team'][0] - t['team'][1]:+.1f}")
print(f"  home court                                 {t['home_court']:+.1f}")
print(f"  back-to-back          {'home tired ' if g['home_b2b'] else ''}{'away tired' if g['away_b2b'] else ''}{'neither' if not (g['home_b2b'] or g['away_b2b']) else ''}{'':>14} {t['b2b']:+.1f}")
print(f"  injury report         {home} missing {g['home_miss']:.1f}, {away} missing {g['away_miss']:.1f}  ->  {t['injury']:+.1f}")
print(f"  box-score players                          {t['box_players']:+.1f}")
print(f"  player ratings (expected lineups)          {t['players']:+.1f}")
print(f"  {'-' * 50}")
print(f"  MODEL: {home} by {t['total']:+.1f}   CLOSE: {home} by {-g['close']:+.1f} ({g['key_book']})   RESULT: {home} by {g['margin']:+d}")
for side, team, lu in (("home", home, t["lineups"][0]), ("away", away, t["lineups"][1])):
    print(f"\n  {team} expected lineup (minutes, points per 48 he adds):")
    for pl, m, r in lu[:9]:
        print(f"    {pl.title():24} {m:4.0f} min   {r:+.1f}")
