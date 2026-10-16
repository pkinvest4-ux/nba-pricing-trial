# NBA pricing model

Prices NBA games with what was known by the end of the day before, and grades the price against the
pre-game closing line.

- **[WRITEUP.md](WRITEUP.md)**: the one-page summary.
- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)**: a walk through the code, in the order a game gets priced.
- **[DETAILS.md](DETAILS.md)**: every number, season by season.

## Run it

Python 3.10 or newer, standard library only. `pdftotext` (from poppler) reads the injury report
PDFs: `brew install poppler` on a Mac.

```bash
./run.sh            # spreads and totals, graded on the tuning season (2024-25)
./run.sh --test     # spreads and totals, graded on the test season (2025-26)
python3 walkforward.py               # each season 2016-17 to 2025-26, tuned on the one before
python3 explain.py WSH DET 2025-11-10 # how one game was priced, piece by piece
```

The first run downloads everything into `data/` and caches it. The 2025-26 injury reports after
Dec 21, 2025 come from a research archive of the NBA's original PDFs (github.com/niksmdmarketing/NFLFutures,
release `nba-official-reports`: `nba-official-reports-2026.zip` and `research/nba_pregame/reparse_v2_2026_reports.json`
on its `market-data` branch), saved under `data/third_party/`.

## Files

| File | Job |
|---|---|
| `data.py` | Everything known the night before a game: the closing line, back-to-backs, injuries, player values, expected lineups |
| `model.py` | The model: price each day's games, then learn from them; choose the settings |
| `evaluate.py` | Grade each step against the close, check which gains are real, win probability |
| `totals.py` | The over/under model |
| `walkforward.py` | Tune on one season, grade the next, for every season 2016-17 to 2025-26 |
| `explain.py` | Show how one game's number was built |
| `fetch_games.py` | Every regular-season game and score, 2014-15 to 2025-26 (ESPN) |
| `fetch_espn_odds.py` | Each book's pre-game open and close: spread, total and moneyline (ESPN) |
| `fetch_boxscores.py` | Player minutes and Game Score for every game (ESPN) |
| `fetch_injuries.py` | The NBA's injury report as it stood at the end of the evening before each game |
| `common.py` | Web requests and team codes shared by the fetch scripts |

## Rules the code follows

- A day's games are priced before any of that day's results, box scores or lines are used.
- Nothing from game day: injuries come from the last report of the evening before.
- Every setting is chosen on an earlier season than the one being graded.
- Each season is graded against one book's pre-game close, as recorded by ESPN.
- Any spread over 30 points, or total outside 170 to 280, is bad data and dropped.
