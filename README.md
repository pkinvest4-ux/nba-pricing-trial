# NBA pricing model (trial)

Prices NBA games with what was known by the end of the day before, and grades the price against
the pre-game closing line. The one-page summary is [WRITEUP.md](WRITEUP.md); the full notes are [DETAILS.md](DETAILS.md).

## Run it

Python 3.10 or newer, standard library only. `pdftotext` (poppler) reads the injury report PDFs:
`brew install poppler` on a Mac.

```bash
./run.sh            # spreads and totals on the tuning season (2024-25)
./run.sh --test     # spreads and totals on the test season (2025-26)
```

The first run downloads everything (ESPN and the NBA's injury reports) into `data/` and caches it.

## Files

| File | What it does |
|---|---|
| `fetch_games.py` | Every regular-season game and score, 2018-19 to 2025-26 (ESPN) |
| `fetch_espn_odds.py` | Each book's pre-game open and close, spread and moneyline (ESPN) |
| `fetch_boxscores.py` | Player minutes and Game Score, 2023-24 to 2025-26 (ESPN) |
| `fetch_injuries.py` | The NBA's official injury report as of 8:30 PM the evening before each game |
| `model.py` | Spread model: team and player ratings, improvements, tuning, grading, win probability |
| `totals.py` | Over/under model: offence and defence ratings, graded against the closing total |
| `experiments.py` | The ideas tried on 2024-25 and 2023-24, and which were kept |
| `check_lines.py`, `check_absence.py` | Data checks described in WRITEUP |
| `fetch_lines.py` | SportsbookReview lines: downloaded and checked, not used (in-game "latest" lines) |

## Rules the code follows

- Each day's games are priced before any of that day's results or lines are used.
- Nothing from game day: injuries come from the report published the evening before.
- Every setting is chosen on 2024-25. The code was frozen before each 2025-26 run (commits `dedd7fd`
  and `ffbb83d`; see DETAILS for why there were two).
- Grading uses one book's pre-game close per game, as recorded by ESPN.
- Any "spread" over 30 points, or total outside 170 to 280, is bad data and dropped.
