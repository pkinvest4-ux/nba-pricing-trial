"""Opening and closing spreads and moneylines from every book SportsbookReview lists, by date,
2021-22 to 2025-26. On a past date, a book's "current" line is its last line before tip-off: its close.
Writes data/lines/<date>.json (cached), one request per second."""
import json, re, pathlib, datetime as dt
from common import fetch
from fetch_games import SEASONS

OUT = pathlib.Path("data/lines")
PAGES = {"spread": "https://www.sportsbookreview.com/betting-odds/nba-basketball/?date={d}",
         "moneyline": "https://www.sportsbookreview.com/betting-odds/nba-basketball/money-line/full-game/?date={d}"}


def rows(html):
    m = re.search(r'__NEXT_DATA__" type="application/json">(.*?)</script>', html or "")
    tables = json.loads(m.group(1))["props"]["pageProps"].get("oddsTables") if m else None
    return tables[0]["oddsTableModel"]["gameRows"] if tables else []


def pull(day):
    f = OUT / f"{day}.json"
    if f.exists():
        return
    games = {}
    for market, url in PAGES.items():
        for g in rows(fetch(url.format(d=day), pause=1.0, as_json=False)):
            v = g["gameView"]
            key = f'{v["awayTeam"]["shortName"]}@{v["homeTeam"]["shortName"]}'
            rec = games.setdefault(key, {"start": v.get("startDate"), "books": {}})
            for ov in g["oddsViews"]:
                if not ov:
                    continue
                b = rec["books"].setdefault(ov["sportsbook"], {})
                for when in ("openingLine", "currentLine"):
                    line = ov.get(when) or {}
                    tag = "open" if when == "openingLine" else "close"
                    if market == "spread":
                        b[f"{tag}_spread"], b[f"{tag}_spread_price"] = line.get("homeSpread"), line.get("homeOdds")
                    else:
                        b[f"{tag}_ml_home"], b[f"{tag}_ml_away"] = line.get("homeOdds"), line.get("awayOdds")
    f.write_text(json.dumps(games))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    days = []
    for season, (a, b) in SEASONS.items():
        if season >= "2021-22":
            a, b = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
            days += [a + dt.timedelta(n) for n in range((b - a).days + 1)]
    for i, d in enumerate(days):
        pull(d)
        if i % 50 == 0:
            print(i, "of", len(days), d, flush=True)
    print("done")
