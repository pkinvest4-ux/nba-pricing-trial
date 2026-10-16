"""Points and plus-minus for every player in every game 2022-23 to 2025-26, from ESPN box scores.
Writes data/plusminus.json: {game_id: {team: {name: [minutes, points, plus_minus]}}}."""
import json, pathlib, concurrent.futures as cf
from common import fetch, team

SEASONS = ("2022-23", "2023-24", "2024-25", "2025-26")


def pull(gid):
    d = fetch(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={gid}")
    out = {}
    for t in (d or {}).get("boxscore", {}).get("players", []):
        block, players = t["statistics"][0], {}
        for a in block["athletes"]:
            if a.get("didNotPlay") or not a.get("stats"):
                continue
            s = dict(zip(block["labels"], a["stats"]))
            try:
                players[a["athlete"]["displayName"]] = [int(s["MIN"] or 0), int(s["PTS"]), int(s["+/-"])]
            except (ValueError, KeyError):
                pass
        out[team(t["team"]["abbreviation"])] = players
    return gid, out


if __name__ == "__main__":
    games = [json.loads(l) for l in open("data/games.jsonl")]
    path = pathlib.Path("data/plusminus.json")
    out = json.loads(path.read_text()) if path.exists() else {}
    todo = [g["id"] for g in games if g["season"] in SEASONS and not out.get(g["id"])]
    with cf.ThreadPoolExecutor(4) as ex:
        out.update(dict(ex.map(pull, todo)))
    path.write_text(json.dumps(out))
    print(len(out), "games,", sum(not v for v in out.values()), "empty")
