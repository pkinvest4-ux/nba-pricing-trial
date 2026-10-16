# Full notes: pricing NBA games the night before

**Result:** on the 2025-26 season (1,230 games, never used to choose a setting), my spreads were
**2.05 points** from the pre-game closing line on average, down from **2.99** for a ratings-only
model. On the 429 games where the night-before injury report exists, they were **1.87** points off.
The same approach prices totals **2.49 points** from the closing total. Every improvement holds up on
the unseen season, and the close is still the better forecast of the final score, as I would expect.

## What the model knows, and when

Every team has a rating in points, and every player a value from his own box scores (Game Score per
minute above a bench player, times his usual minutes). Predicted home margin = home rating minus away
rating, plus home-court advantage, plus the gap in strength between the players expected to be
available, plus two things known the night before: a team on the second night of a back-to-back, and
regulars listed Out, Doubtful or Questionable on the NBA's injury report. Because players carry their
own value, the team rating only has to learn what the players do not explain.

The model walks through seasons one day at a time. It prices every game on a day first, then learns
from that day's results and closing lines. Nothing from game day is used: injury information is the
NBA's report as it stood at 8:30 PM the evening before.

## The answer key, and the data problems behind it

You asked for Pinnacle's close. Its history is only sold commercially, so I looked for free sources.

- **SportsbookReview** has opening and "latest" lines from five to nine books per game. Checking it
  against ESPN, I found its "latest" line is sometimes an in-game line: for Jazz at Nuggets on
  Dec 22, 2025, two books show Denver -23.5 and -24.5 against a -12.5 pre-game close, in a game
  Denver won by 23. Grading against that would leak the result into the answer key, so I dropped it.
- **ESPN** records each book's pre-game open and close, and keeps in-game odds under a separate
  "Live Odds" label. Its closes moved toward the result at a normal rate, with no sign of live lines.
- So the answer key is **one book's pre-game close as recorded by ESPN**: ESPN BET for 2024-25, and
  DraftKings for 2025-26 (971 games), falling back to ESPN BET for the 259 early-season games before
  ESPN changed partners.
- **The NBA's injury report archive stops on Dec 21, 2025.** Later games get no injury adjustment,
  which is why I report the 429 games that have it separately.
- Other fixes: a sanity rule drops "spreads" over 30 and totals outside 170 to 280 (ESPN once stored
  prices like -110 in those fields), All-Star games are removed, and traded players stop counting
  for their old team.

## How I tested it

I chose every setting on 2024-25, checked new ideas on 2023-24 as well, and froze the code in git
before each run on 2025-26. Each gain is checked by comparing two models on the same games and
resampling them 10,000 times: if the gain shows up in 95% of resamples, it is not luck.

**To be transparent:** the spread model was run on 2025-26 three times: a first version (commit
`dedd7fd`, 2.14 points), with box-score player values (commit `ffbb83d`, 2.10), and with full player
ratings (commit `a6fa830`, 2.05). Each addition was chosen on 2024-25 before its run. Full player
ratings gained +0.065 on 2024-25 but only +0.007 on 2023-24, which has no injury reports; with the
reports switched off, 2024-25's gain also fell to +0.014, so the value is in using the report to set
the expected lineup. The totals model was run once.

## Results on 2025-26

| Spread model | Points off the close (1,230 games) | With injury report (429 games) |
|---|---|---|
| Ratings from results only | 2.99 | 2.88 |
| + learn from past closing lines | 2.44 | 2.42 |
| + second night of a back-to-back | 2.21 | 2.15 |
| + night-before injury report | 2.14 | **1.92** |
| + box-score player values | 2.10 | 1.93 |
| + full player ratings with expected lineups | **2.05** | **1.87** |

- **Past closes:** +0.55 points (95% range 0.43 to 0.67). The market knows things a box score does not.
- **Back-to-backs:** worth about 2 points to the rested team. +0.23 (0.17 to 0.29).
- **Injury report:** +0.22 where it exists (0.11 to 0.34), +0.08 over the full season.
- **Box-score player values:** +0.04 (0.02 to 0.05), the same gain as on 2024-25 and 2023-24.
- **Full player ratings:** +0.05 (0.02 to 0.08). Each player's points per 48 minutes is learned mostly
  from closing lines (learning from results alone barely helped). On the injury-report games: +0.06
  (-0.01 to 0.13), not statistically clear on 429 games.
- **Against the final score:** the close misses by 10.88 points, my model by 11.17.

**Win probability**, as a second number: 5.2 percentage points from the no-vig closing price on
average; log loss 0.587 against the close's 0.570 and a coin flip's 0.693. Calibration is good in the
middle (when I said 60 to 80%, the home team won 74%) and a little overconfident at the extremes.
The tuning seasons did not support widening the curve, so I did not adjust it to fit the test.

## Totals (over/under)

Each team gets an offence and a defence rating, around a league scoring level that drifts over time.

| Totals model | Points off the closing total (1,230 games) |
|---|---|
| Ratings from results only | 3.59 |
| + learn from past closing totals | 2.58 |
| + back-to-backs (tired teams score about 0.5 less) | 2.55 |
| + injury report (missing regulars lower their team's points) | **2.49** |

Every step is real on 2025-26, and 2.49 matches the tuning season exactly. The close still beats the
model on the real totals (14.56 against 14.79 points off).

## What did not work

Each was chosen on 2024-25, checked on 2023-24, and dropped because the gain was noise: players
returning from injury, three games in four nights, rest-day differences, time zones crossed, capping
blowout margins, faster learning early in the season, a separate home-court edge for each team, and
"regulars who sat out the previous game". The common reason: the model already learns from every past
closing line, and the market had priced those things in. Back-to-backs and tomorrow's injury report
are the schedule and news effects strong enough to add something on top.

## What I would do next

Find day-before injury news for 2026 (another archive, or saving the report each night going
forward), project each player's minutes instead of using his average, and add pace to the totals.


## Update: ten-season walk-forward, and the injury archive

This section supersedes the 2025-26 numbers above.

**Walk-forward.** For each season from 2016-17 to 2025-26, every setting was chosen on the season
before it and the season was graded once (`walkforward.py`, code frozen at `f2b6ce7` before the run).

| Season | Tuned on | Ratings only | + closes | + back-to-backs | + injuries | + box-score players | + player ratings | Graded against |
|---|---|---|---|---|---|---|---|---|
| 2016-17 | 2015-16 | 2.02 | 1.57 | 1.51 | 1.51 | 1.45 | 1.44 | ESPN consensus |
| 2017-18 | 2016-17 | 2.60 | 1.91 | 1.84 | 1.84 | 1.81 | 1.81 | ESPN consensus |
| 2018-19 | 2017-18 | 2.45 | 1.93 | 1.74 | 1.74 | 1.65 | 1.64 | ESPN consensus |
| 2019-20 | 2018-19 | 2.88 | 2.33 | 2.14 | 2.14 | 2.11 | 2.10 | ESPN consensus |
| 2020-21 | 2019-20 | 3.09 | 2.74 | 2.54 | 2.54 | 2.45 | 2.43 | ESPN consensus |
| 2021-22 | 2020-21 | 2.64 | 2.27 | 2.10 | 2.10 | 2.03 | 1.79 | ESPN consensus |
| 2022-23 | 2021-22 | 3.04 | 2.42 | 2.24 | 1.97 | 1.95 | 1.89 | ESPN consensus |
| 2023-24 | 2022-23 | 2.81 | 2.34 | 2.08 | 1.89 | 1.80 | 1.79 | ESPN BET close |
| 2024-25 | 2023-24 | 2.85 | 2.43 | 2.25 | 2.04 | 2.00 | 1.96 | ESPN BET close |
| 2025-26 | 2024-25 | 3.00 | 2.44 | 2.21 | 2.02 | 2.00 | 1.99 | DraftKings / ESPN BET close |

Real gains (95% range above zero): past closes 10 of 10 seasons, back-to-backs 10 of 10, box-score
player values 9 of 10, full player ratings 4 of 10 (never negative). Injuries were a real gain in all
4 seasons whose tuning season had injury reports; in 2021-22 the tuning season (2020-21) had none, so
the injury weight was set to zero. ESPN's consensus line before 2023-24 is not labelled as a close, so
compare steps within a season rather than levels across eras.

**Injury archive.** After Dec 21, 2025 the NBA moved to quarter-hour report files whose addresses no
longer work. The reports for the rest of 2025-26 come from a research archive of the original PDFs
(github.com/niksmdmarketing/NFLFutures, release `nba-official-reports`). Checks: all 732 files match
their sha256; the 30 files that overlap with reports downloaded from the NBA parse identically. With it,
1,201 of 1,231 games in 2025-26 have a night-before report (up from 430).

**2025-26, final:** spreads 1.99 points off the close (injuries +0.19, 0.13 to 0.26, over the full
season); win probability 5.0 points from the no-vig close, log loss 0.585 vs 0.570; totals 2.44 points
off the closing total (injuries +0.12, 0.07 to 0.17). Close better on real margins by 0.25 (spreads)
and 0.21 (totals).
