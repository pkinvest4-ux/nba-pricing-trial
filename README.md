# Pricing NBA Spreads the Night Before

Prices every NBA game with what was known by the end of the day before, and grades the price against
the pre-game closing line. On 2025-26 the model's spreads were **1.99 points** off the close on
average, down from 3.00 for a ratings-only model.

## Start here

1. **[WRITEUP.md](WRITEUP.md):** the one-page summary.
2. **[HOW_IT_WORKS.md](HOW_IT_WORKS.md):** a walk through the code, in the order a game gets priced.
3. **[DETAILS.md](DETAILS.md):** every number, season by season.
4. **[results_by_game.csv](results_by_game.csv):** every game of 2024-25 and 2025-26: how each number was
   built, the close and the result. [results_summary.csv](results_summary.csv) has the season totals.

## Run it

Python 3.10 or newer, standard library only. `pdftotext` (from poppler) reads the injury report PDFs:
`brew install poppler` on a Mac.

```bash
./run.sh --test                       # spreads and totals, graded on the test season (2025-26)
./run.sh                              # the same, graded on the tuning season (2024-25)
python3 walkforward.py                # each season 2016-17 to 2025-26, tuned on the one before
python3 explain.py WSH DET 2025-11-10 # how one game was priced, piece by piece
python3 export_results.py             # rewrite the two spreadsheets
```

The first run downloads everything into `data/` and caches it. The two experiments also need
`python3 fetch_plusminus.py` and `python3 fetch_winshares.py` first.

The 2025-26 injury reports after Dec 21, 2025 come from a research archive of the NBA's original PDFs
(github.com/niksmdmarketing/NFLFutures, release `nba-official-reports`: `nba-official-reports-2026.zip`
and `research/nba_pregame/reparse_v2_2026_reports.json` on its `market-data` branch), saved under
`data/third_party/`.

## Files

**The model**

| File | Job |
|---|---|
| `data.py` | Everything known the night before a game: the closing line, back-to-backs, injuries, player values, expected lineups |
| `model.py` | Price each day's games, then learn from them; choose the settings |
| `totals.py` | The over/under model |

**Grading and results**

| File | Job |
|---|---|
| `evaluate.py` | Grade each step against the close, check which gains are real, win probability |
| `walkforward.py` | Tune on one season, grade the next, for every season 2016-17 to 2025-26 |
| `explain.py` | Show how one game's number was built |
| `export_results.py` | Write `results_by_game.csv` and `results_summary.csv` |

**Experiments that did not beat the final model** (results in [DETAILS.md](DETAILS.md))

| File | Job |
|---|---|
| `pooled.py` | Tune on several past seasons at once |
| `player_values.py` | Value players by plus-minus, points, win shares or BPM instead of Game Score |

**Downloads**

| File | Job |
|---|---|
| `fetch_games.py` | Every regular-season game and score, 2014-15 to 2025-26 (ESPN) |
| `fetch_espn_odds.py` | Each book's pre-game open and close: spread, total and moneyline (ESPN) |
| `fetch_boxscores.py` | Player minutes and Game Score for every game (ESPN) |
| `fetch_injuries.py` | The NBA's injury report as it stood at the end of the evening before each game |
| `fetch_plusminus.py` | Points and plus-minus for every player, 2022-23 to 2025-26 (ESPN) |
| `fetch_winshares.py` | Each player's season win shares and BPM (Basketball-Reference) |
| `common.py` | Web requests and team codes shared by the fetch scripts |

## Rules the code follows

- A day's games are priced before any of that day's results, box scores or lines are used.
- Injuries come from the last report of the evening before. Nothing from game day is used.
- Every setting is chosen on an earlier season than the one being graded.
- Each season is graded against one book's pre-game close, as recorded by ESPN.
- Any spread over 30 points, or total outside 170 to 280, is bad data and dropped.
