# Full notes

Every number behind [WRITEUP.md](WRITEUP.md). For how the code works, see [HOW_IT_WORKS.md](HOW_IT_WORKS.md).
All figures are points between the model's number and the line, averaged over games, unless stated.

## Data

- **Answer key.** One book's pre-game close per season, as recorded by ESPN, which keeps in-game odds
  under separate "Live Odds" entries: ESPN BET for 2023-24 and 2024-25; DraftKings for 971 games of
  2025-26 and ESPN BET for the 259 early-season games before ESPN changed partners (one game had
  neither, and uses the median of the books ESPN lists). Seasons before 2023-24 have no labelled close
  in ESPN's data and use the best line ESPN lists, almost always its consensus line.
- **Injuries.** The NBA's official injury report as it stood at the end of the evening before each game,
  for 2021-22 to 2025-26. From Dec 22, 2025 the NBA published quarter-hour files whose addresses no
  longer work; those reports come from a research archive of the original PDFs. Checks: all 732 files
  match their sha256 checksums, and the 30 files that overlap with reports downloaded from the NBA parse
  identically. 1,201 of 1,231 games in 2025-26 have a night-before report.
- **Games, odds and box scores** from ESPN, 2014-15 to 2025-26 (14,443 games). All-Star and exhibition
  games are removed. Spreads over 30 points and totals outside 170 to 280 are treated as bad data.

## Final settings (chosen on 2024-25)

| Setting | Value | Meaning |
|---|---|---|
| `k` | 0.01 | team ratings move 1% of the way toward each result |
| `k_market` | 0.1 | and 10% of the way toward each closing line |
| `hca` | 2.0 | home-court advantage, points |
| `carry` | 0.7 | share of a team rating kept into a new season |
| `b2b` | 2.0 | points given up on the second night of a back-to-back |
| `inj` | 0.1 | weight on the gap in missing rotation value |
| `roster` | 0.05 | weight on the gap in available players' box-score value |
| `p_w`, `p_mkt`, `p_k`, `p_carry` | 0.75, 0.015, 0.001, 1.0 | player ratings: weight, learning from closes, from results, carry-over |

## Spreads, 2025-26 (test season)

| Step | Off the close | Gain (95% range) | Off the open |
|---|---|---|---|
| Ratings from results only | 3.00 | | 2.64 |
| + learn from past closing lines | 2.44 | +0.55 (0.43 to 0.67) | 2.11 |
| + back-to-backs | 2.21 | +0.23 (0.17 to 0.29) | 2.00 |
| + night-before injury report | 2.02 | +0.19 (0.13 to 0.26) | 1.87 |
| + box-score player values | 2.00 | +0.02 (0.00 to 0.04) | 1.84 |
| + player ratings | **1.99** | +0.00 (-0.04 to 0.05) | **1.77** |

Against the actual margin: model 11.13 points off, close 10.88 (close better by 0.25, 0.11 to 0.39).
On the 1,201 games with a night-before report: 1.94 off the close, injuries +0.20 (0.13 to 0.26).

**2024-25 (tuning season):** 2.80 from results only, 1.88 for the full model; the close beat the model
on actual margins by 0.24.

## Win probability, 2025-26

Actual margins land around the prediction with a spread of 12.9 points (measured on earlier seasons),
which turns each margin into a win probability. Graded against the no-vig closing moneyline:

- Average gap to the closing price: 5.0 percentage points.
- Log loss: model 0.585, close 0.570, coin flip 0.693 (close better by 0.015, 0.007 to 0.024).
- Calibration: when the model said 20 to 40%, the home team won 32%; 40 to 60%, 48%; 60 to 80%, 72%;
  80 to 100%, 84%.

## Totals

Offence and defence ratings around a drifting league average (settings: `k` 0.05, `carry` 0.5, league
drift 0.005, `k_market` 0.5, back-to-back -0.5 points, injury weight -1).

| Step | 2024-25 (tuning) | 2025-26 (test) | Gain on 2025-26 (95% range) |
|---|---|---|---|
| Ratings from results only | 3.49 | 3.59 | |
| + learn from past closing totals | 2.66 | 2.58 | +1.01 (0.87 to 1.15) |
| + back-to-backs | 2.64 | 2.55 | +0.03 (0.01 to 0.05) |
| + night-before injury report | 2.51 | **2.44** | +0.12 (0.07 to 0.17) |

Against the actual total on 2025-26: model 14.77 points off, close 14.56 (close better by 0.21).

## Ten seasons, each tuned on the season before (`walkforward.py`)

| Season | Tuned on | Results only | + closes | + back-to-backs | + injuries | + box-score players | + player ratings |
|---|---|---|---|---|---|---|---|
| 2016-17 | 2015-16 | 2.02 | 1.57 | 1.51 | 1.51 | 1.45 | 1.44 |
| 2017-18 | 2016-17 | 2.60 | 1.91 | 1.84 | 1.84 | 1.81 | 1.81 |
| 2018-19 | 2017-18 | 2.45 | 1.93 | 1.74 | 1.74 | 1.65 | 1.64 |
| 2019-20 | 2018-19 | 2.88 | 2.33 | 2.14 | 2.14 | 2.11 | 2.10 |
| 2020-21 | 2019-20 | 3.09 | 2.74 | 2.54 | 2.54 | 2.45 | 2.43 |
| 2021-22 | 2020-21 | 2.64 | 2.27 | 2.10 | 2.10 | 2.03 | 1.79 |
| 2022-23 | 2021-22 | 3.04 | 2.42 | 2.24 | 1.97 | 1.95 | 1.89 |
| 2023-24 | 2022-23 | 2.81 | 2.34 | 2.08 | 1.89 | 1.80 | 1.79 |
| 2024-25 | 2023-24 | 2.85 | 2.43 | 2.25 | 2.04 | 2.00 | 1.96 |
| 2025-26 | 2024-25 | 3.00 | 2.44 | 2.21 | 2.02 | 2.00 | 1.99 |

Real gains (95% range above zero): past closes 10 of 10 seasons; back-to-backs 10 of 10; box-score
players 9 of 10; player ratings 4 of 10, never negative. Injury reports exist from 2021-22, so injuries
can be learned from 2022-23 on, and were a real gain in all 4 of those seasons (in 2021-22 the tuning
season had no reports, so its weight was zero). Player ratings mattered most where the injury step
could not help: 2021-22, +0.24. Before 2023-24 the line is ESPN's consensus rather than a labelled
close, so compare steps within a season rather than levels across seasons.

## Order of work

The code was frozen in git before each run on 2025-26. Before the ten-season run, the spread model was
graded on 2025-26 three times as pieces were added: a first version (commit `dedd7fd`, 2.14), with
box-score player values (`ffbb83d`, 2.10) and with player ratings (`a6fa830`, 2.05). Each addition was
chosen on 2024-25 first. The ten-season run (`f2b6ce7`) is the cleaner evidence, since every season is
graded with settings chosen only on earlier data. The figures above use the final data (injury reports
for nearly all of 2025-26), which is why 2025-26 reads 1.99 rather than 2.05.
