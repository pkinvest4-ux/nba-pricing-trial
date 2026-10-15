"""Pre-game opening and closing lines per book from ESPN, for every game.

ESPN keeps in-game odds under separate providers named '... - Live Odds', so a book's 'close' here is its
last PRE-GAME line. (SportsbookReview's 'latest' line turned out to include in-game odds; see WRITEUP.)
Writes data/espn_odds.json: {game_id: {book: {open_spread, close_spread, open_total, close_total, ...}}}
Spreads are the home team's line, negative = home favoured."""
import json, pathlib, concurrent.futures as cf
from common import fetch


def num(v):
    if isinstance(v, dict):
        v = v.get("american") or v.get("alternateDisplayValue") or v.get("value")
    if v in (None, ""):
        return None
    if str(v).upper() == "EVEN":
        return 100.0
    try:
        return float(str(v).replace("+", "").lstrip("ouOU"))  # totals look like 'o224.5' 
    except ValueError:
        return None


def pull(gid):
    d = fetch(f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{gid}/competitions/{gid}/odds?limit=50")
    books = {}
    for it in (d or {}).get("items", []):
        name = (it.get("provider") or {}).get("name") or ""
        if "Live" in name:
            continue  # in-game odds
        h, a = it.get("homeTeamOdds") or {}, it.get("awayTeamOdds") or {}
        rec = {"spread": num(it.get("spread")), "total": num(it.get("overUnder"))}
        for when in ("open", "close"):
            rec[f"{when}_total"] = num(((it.get(when) or {}).get("total")))
            rec[f"{when}_spread"] = num((h.get(when) or {}).get("pointSpread"))
            rec[f"{when}_ml_home"] = num((h.get(when) or {}).get("moneyLine"))
            rec[f"{when}_ml_away"] = num((a.get(when) or {}).get("moneyLine"))
        books[name] = rec
    return gid, books


if __name__ == "__main__":
    games = [json.loads(l) for l in open("data/games.jsonl")]
    with cf.ThreadPoolExecutor(8) as ex:
        out = dict(ex.map(pull, [g["id"] for g in games]))
    pathlib.Path("data/espn_odds.json").write_text(json.dumps(out))
    print(len(out), "games,", sum(not v for v in out.values()), "without odds")
