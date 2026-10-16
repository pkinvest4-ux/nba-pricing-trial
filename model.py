"""The spread model: price each day's games, then learn from them.

Predicted home margin =
      home team rating - away team rating        (learned from results and past closing lines)
    + home-court advantage
    + back-to-back penalty                        (b2b points to the rested team)
    + injury adjustment                           (inj x the gap in missing rotation value)
    + box-score player strength                   (roster x the gap in expected players' value)
    + player ratings of the expected lineups      (p_w x the gap, each player in points per 48 minutes)

After a day's games are played:
    team ratings move toward the actual margin (k) and toward the closing line (k_market);
    player ratings move toward both (p_k, p_mkt), shared among those who played, by minutes.
At the start of each season every rating shrinks toward average (carry, p_carry).
"""
import statistics as st
from data import game_days, TUNE


def run(games, k=0.03, hca=2.5, carry=0.7, k_market=0.0, b2b=0.0, inj=0.0, roster=0.0,
        p_w=0.0, p_k=0.0, p_mkt=0.0, p_carry=0.8, trace=None):
    """Walk through every season one day at a time. Returns each game's predicted home margin.
    Pass a dict as `trace` to record how each game's number was built (used by explain.py)."""
    team, player, season, preds = {}, {}, None, []
    for day in game_days(games):
        if day[0]["season"] != season:  # a new season: ratings shrink toward average
            season = day[0]["season"]
            team = {t: r * carry for t, r in team.items()}
            player = {pl: r * p_carry for pl, r in player.items()}

        # 1. Price every game on the day, using only what was known before it.
        day_preds = []
        for g in day:
            both_lineups = g["home_exp"] and g["away_exp"]
            parts = {
                "team": team.get(g["home"], 0.0) - team.get(g["away"], 0.0),
                "home_court": 0 if g["neutral"] else hca,
                "b2b": b2b * (g["away_b2b"] - g["home_b2b"]),
                "injury": inj * (g["away_miss"] - g["home_miss"]),
                "box_players": roster * (g["home_roster"] - g["away_roster"])
                               if g["home_roster"] and g["away_roster"] else 0.0,
                "players": p_w * (lineup_minutes(player, g["home_exp"]) - lineup_minutes(player, g["away_exp"])) / 48
                           if both_lineups else 0.0,
            }
            p = sum(parts.values())
            day_preds.append(p)
            if trace is not None:
                trace[g["id"]] = dict(parts, total=p, ratings=(team.get(g["home"], 0.0), team.get(g["away"], 0.0)),
                                      lineups=tuple(sorted(((pl, m, player.get(pl, 0.0)) for pl, m in g[s + "_exp"]),
                                                           key=lambda x: -x[1]) for s in ("home", "away")))
        preds.extend(day_preds)

        # 2. Only now learn from the day's results and closing lines.
        for g, p in zip(day, day_preds):
            miss_result = g["margin"] - p                                       # how wrong we were on the score
            miss_close = (-g["close"] - p) if g["close"] is not None else None  # and against the market
            team[g["home"]] = team.get(g["home"], 0.0) + k * miss_result
            team[g["away"]] = team.get(g["away"], 0.0) - k * miss_result
            if p_k or p_mkt:  # share the miss among the players who actually played, by minutes
                step = p_k * miss_result + (p_mkt * miss_close if p_mkt and miss_close is not None else 0.0)
                for pl, m in g["home_act"]:
                    player[pl] = player.get(pl, 0.0) + step * m / 48
                for pl, m in g["away_act"]:
                    player[pl] = player.get(pl, 0.0) - step * m / 48
            if k_market and miss_close is not None:
                team[g["home"]] += k_market * miss_close
                team[g["away"]] -= k_market * miss_close
    return preds


def lineup_minutes(player, lineup):
    """Sum of each expected player's rating (points per 48 minutes) times his expected minutes.
    Divided by 48, this is the lineup's strength in points."""
    return sum(player.get(pl, 0.0) * m for pl, m in lineup)


# ---------- choosing the settings ----------

def gaps(games, preds, season, line="close", only=None):
    """Points between our number and the line, for every graded game in a season (or a list of seasons)."""
    seasons = {season} if isinstance(season, str) else set(season)
    return [abs(p + g[line]) for g, p in zip(games, preds)
            if g["season"] in seasons and g[line] is not None and (only is None or only(g))]


def tune(games, grid, season=None):
    """Try every setting in `grid` and keep the one closest to the close on `season`."""
    season = season or TUNE
    return min(((st.mean(gaps(games, run(games, **p), season)), p) for p in grid), key=lambda x: x[0])


def tuned_models(games, season=None):
    """Build the model one step at a time, choosing each step's settings on `season` (default 2024-25).
    Returns every step, so each one's contribution can be measured."""
    grid = [dict(k=k, hca=h, carry=c) for k in (0.01, 0.02, 0.03, 0.04, 0.05, 0.07)
            for h in (1.5, 2.0, 2.5, 3.0, 3.5) for c in (0.4, 0.55, 0.7, 0.85)]
    _, base = tune(games, grid, season)
    _, closes = tune(games, [dict(base, k_market=x) for x in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4)], season)
    _, rest = tune(games, [dict(closes, b2b=x) for x in (0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)], season)
    _, injuries = tune(games, [dict(rest, inj=x) for x in (0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5)], season)
    _, box = tune(games, [dict(injuries, roster=w, k=k) for w in (0.02, 0.03, 0.05, 0.07, 0.1)
                          for k in (0.015, 0.02, 0.025, 0.03)], season)
    _, players = tune(games, [dict(box, p_w=0.75, p_carry=1.0, p_k=0.001, p_mkt=pm, k_market=km, k=k, inj=i)
                              for pm in (0.015, 0.02, 0.025) for km in (0.1, 0.15) for k in (0.01, 0.02)
                              for i in (0.1, 0.15)], season)
    return {"baseline": base, "+ past closes": closes, "+ back-to-backs": rest, "+ injuries": injuries,
            "+ box-score players": box, "+ player ratings": players}
