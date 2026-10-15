"""Player minutes and Game Score for every game 2021-22 to 2025-26, from ESPN box scores.
Writes data/boxscores.json: {game_id: {team: [{"name", "min", "gmsc"}]}}."""
import json, pathlib, concurrent.futures as cf
from common import fetch, team

SEASONS = ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26")


def made_att(s):
    m, a = s.split("-")
    return int(m), int(a)


def game_score(s):
    """John Hollinger's Game Score: one number for a player's whole box-score line."""
    (fg, fga), (ft, fta) = made_att(s["FG"]), made_att(s["FT"])
    return (int(s["PTS"]) + 0.4 * fg - 0.7 * fga - 0.4 * (fta - ft) + 0.7 * int(s["OREB"]) + 0.3 * int(s["DREB"])
            + int(s["STL"]) + 0.7 * int(s["AST"]) + 0.7 * int(s["BLK"]) - 0.4 * int(s["PF"]) - int(s["TO"]))


def pull(gid):
    d = fetch(f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={gid}")
    out = {}
    for t in (d or {}).get("boxscore", {}).get("players", []):
        block, players = t["statistics"][0], []
        for a in block["athletes"]:
            if a.get("didNotPlay") or not a.get("stats"):
                continue
            s = dict(zip(block["labels"], a["stats"]))
            try:
                players.append({"name": a["athlete"]["displayName"], "min": int(s["MIN"] or 0),
                                "gmsc": round(game_score(s), 2)})
            except (ValueError, KeyError):
                pass
        out[team(t["team"]["abbreviation"])] = players
    return gid, out


if __name__ == "__main__":
    games = [json.loads(l) for l in open("data/games.jsonl")]
    path = pathlib.Path("data/boxscores.json")
    out = json.loads(path.read_text()) if path.exists() else {}  # keep what is already downloaded
    todo = [g["id"] for g in games if g["season"] in SEASONS and g["id"] not in out]
    with cf.ThreadPoolExecutor(8) as ex:
        out.update(dict(ex.map(pull, todo)))
    path.write_text(json.dumps(out))
    print(len(out), "box scores,", sum(not v for v in out.values()), "empty")
