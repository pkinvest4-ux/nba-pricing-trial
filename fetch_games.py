"""Every completed NBA regular-season game, 2014-15 to 2025-26, from ESPN's public scoreboard.
Writes data/games.jsonl. All-Star and other exhibition games are dropped."""
import json, datetime as dt, concurrent.futures as cf, pathlib
from common import fetch, team, NBA

SEASONS = {
    "2014-15": ("2014-10-27", "2015-04-16"), "2015-16": ("2015-10-26", "2016-04-14"),
    "2016-17": ("2016-10-24", "2017-04-13"), "2017-18": ("2017-10-16", "2018-04-12"),
    "2018-19": ("2018-10-15", "2019-04-12"), "2019-20": ("2019-10-21", "2020-08-16"),
    "2020-21": ("2020-12-21", "2021-05-17"), "2021-22": ("2021-10-18", "2022-04-11"),
    "2022-23": ("2022-10-17", "2023-04-10"), "2023-24": ("2023-10-23", "2024-04-15"),
    "2024-25": ("2024-10-21", "2025-04-14"), "2025-26": ("2025-10-20", "2026-04-13"),
}


def day_games(args):
    season, day = args
    d = fetch(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day:%Y%m%d}&seasontype=2&limit=100")
    if d is None:
        raise RuntimeError(f"ESPN did not answer for {day}; rerun rather than lose that day's games")
    out = []
    for ev in (d or {}).get("events", []):
        c = ev["competitions"][0]
        if not c["status"]["type"].get("completed"):
            continue
        t = {x["homeAway"]: x for x in c["competitors"]}
        home, away = team(t["home"]["team"]["abbreviation"]), team(t["away"]["team"]["abbreviation"])
        if home not in NBA or away not in NBA:
            continue
        out.append({"id": ev["id"], "season": season, "date": ev["date"], "home": home, "away": away,
                    "home_pts": int(t["home"]["score"]), "away_pts": int(t["away"]["score"]),
                    "neutral": c.get("neutralSite", False)})
    return out


if __name__ == "__main__":
    jobs = []
    for season, (a, b) in SEASONS.items():
        a, b = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
        jobs += [(season, a + dt.timedelta(n)) for n in range((b - a).days + 1)]
    with cf.ThreadPoolExecutor(8) as ex:
        games = [g for day in ex.map(day_games, jobs) for g in day]
    games.sort(key=lambda g: g["date"])
    pathlib.Path("data/games.jsonl").write_text("\n".join(json.dumps(g) for g in games))
    print(len(games), "games")
