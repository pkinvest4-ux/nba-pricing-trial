"""Sanity check: does SportsbookReview's DraftKings close match ESPN's DraftKings close?
If they agree on most games, SBR's 'current line' on past dates really is the closing line."""
import json, random, statistics as st, concurrent.futures as cf
from common import fetch, team
import model


def espn_dk_close(gid):
    d = fetch(f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/{gid}/competitions/{gid}/odds?limit=50")
    for it in (d or {}).get("items", []):
        if (it.get("provider") or {}).get("name") == "DraftKings":
            v = ((it.get("homeTeamOdds") or {}).get("close") or {}).get("pointSpread")
            if isinstance(v, dict):
                v = v.get("american") or v.get("alternateDisplayValue")
            try:
                return float(str(v).replace("+", ""))
            except (TypeError, ValueError):
                return None
    return None


if __name__ == "__main__":
    games = [json.loads(l) for l in open("data/games.jsonl")]
    sbr = {}
    import os
    for f in os.listdir("data/lines"):
        for key, rec in json.load(open(f"data/lines/{f}")).items():
            away, home = (team(x) for x in key.split("@"))
            dk = rec["books"].get("draftkings", {}).get("close_spread")
            if dk is not None:
                sbr[(f[:-5], home, away)] = dk
    pool = [g for g in games if g["season"] in ("2024-25", "2025-26")
            and (model.local_day(g).isoformat(), g["home"], g["away"]) in sbr]
    sample = random.Random(1).sample(pool, min(300, len(pool)))
    with cf.ThreadPoolExecutor(8) as ex:
        espn = list(ex.map(lambda g: espn_dk_close(g["id"]), sample))
    pairs = [(sbr[(model.local_day(g).isoformat(), g["home"], g["away"])], e) for g, e in zip(sample, espn) if e is not None]
    same = sum(a == b for a, b in pairs)
    print(f"{len(pairs)} games with both: identical {same / len(pairs):.0%}, within half a point "
          f"{sum(abs(a - b) <= 0.5 for a, b in pairs) / len(pairs):.0%}, average difference {st.mean(abs(a - b) for a, b in pairs):.2f}")
