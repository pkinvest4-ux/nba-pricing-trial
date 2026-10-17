# Pricing NBA Spreads the Night Before

**Patrick Kooy Velazquez** · Trial task for Jaden Kwek · October 2026

**The result:** my starting model was **3.00 points** off the pre-game close on 2025-26. With the
improvements, it's **1.99**.

---

## 1. The model

I price each game the night before. The predicted home margin is the sum of six parts:

1. **Team ratings:** the gap between the two teams' ratings, in points.
2. **Home court:** the same for every home team.
3. **Back-to-backs:** points a team gives up on its second night in a row.
4. **Injuries:** the value of the regulars listed out on the NBA's injury report the night before.
5. **Box-score players:** the strength gap between the players expected to play.
6. **Player ratings:** the gap between the two expected lineups, with each player rated in points.

The model walks through the schedule one day at a time. It prices a day's games, then learns from
their results and closing lines before moving on to the next day.

## 2. The data

- **Closing lines:** ESPN's recorded pre-game closes. That's ESPN BET through 2024-25 and DraftKings for
  most of 2025-26. Seasons before 2023-24 use ESPN's consensus line.
- **Injuries:** the NBA's official injury report as it stood at the end of the evening before each game.
  Reports after Dec 21, 2025 come from a research archive of the original PDFs, which I checked against
  my own NBA downloads.
- **Results and player minutes:** ESPN box scores, back to 2014-15.

## 3. How I tested it

I chose every setting on 2024-25, then graded 2025-26 once. To make sure one season wasn't luck, I
repeated the whole process for each of the last ten seasons, tuning on the season before each one. I
only count a gain as real if it holds in 95% of 10,000 resamples of the games.

## 4. Results

| Step (2025-26) | Off the close | Gain (95% range) | Real gain in the last 10 seasons |
|---|---|---|---|
| Starting model: team ratings and home court | 3.00 | | |
| + learn from past closing lines | 2.44 | +0.55 (0.43 to 0.67) | 10 of 10 |
| + second night of a back-to-back | 2.21 | +0.23 (0.17 to 0.29) | 10 of 10 |
| + night-before injury report | 2.02 | +0.19 (0.13 to 0.26) | 4 of 4 with reports to learn from |
| + box-score player values | 2.00 | +0.02 (0.00 to 0.04) | 9 of 10 |
| + full player ratings | **1.99** | +0.00 (-0.04 to 0.05) | 4 of 10 |

- Learning from past closing lines is the biggest improvement, and it was real in every one of the ten
  seasons.
- Across the ten seasons, the improvements beat the starting model by 0.6 to 1.1 points every year.
- Player ratings added almost nothing on 2025-26. I kept them because they never made a season worse.
- Against the final scores, the close still beats me: it's 10.88 points off on average, and I'm 11.13.

## 5. Second numbers

- **Win probability:** 5.0 percentage points from the no-vig closing price, with a log loss of 0.585
  against the close's 0.570.
- **Totals:** 3.59 down to **2.44 points** off the closing total, with every step real.

## 6. Order of work

Before the ten-season run, I graded 2025-26 three times as I added pieces (2.14, 2.10, 2.05). Each piece
was chosen on 2024-25 first, with the code frozen in git before it was graded. The ten-season run is the
cleaner test, since every season is graded with settings chosen only on earlier seasons.

## 7. Next

Projected minutes for each player, pace for totals, and saving the injury report every night.

The full numbers are in [DETAILS.md](DETAILS.md), and every game is in [results_by_game.csv](results_by_game.csv).
