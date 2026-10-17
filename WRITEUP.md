# Pricing NBA Spreads the Night Before

**Patrick Kooy Velazquez** · Trial task for Jaden Kwek · October 2026

**The result:** my starting model was **3.00 points** off the pre-game close on 2025-26. With the
improvements, it's **1.99**.

---

## 1. The model

I price each game the night before, walking through the schedule one day at a time: price the day's
games, then learn from their results and closing lines before the next day.

**Starting model.** Every team starts at 0. After each game, both teams' ratings move 1% of the way
toward the actual result: if I had Detroit by 5 and they won by 15, Detroit goes up a little and its
opponent goes down a little. The predicted margin is the rating gap plus 2 points of home court. Each
new season, teams keep 70% of their rating, since rosters change. That's the 3.00.

**Improvements, one at a time:**

1. **Learn from past closing lines.** Ratings also move toward each game's closing line, not just the
   score. The market knows things a box score doesn't. (2.44)
2. **Back-to-backs.** A team on its second night in a row gives up 2 points. (2.21)
3. **Injury report.** Regulars listed out the night before cost their team their value. (2.02)
4. **Box-score players.** The strength of the players expected to play. (2.00)
5. **Player ratings.** Each player gets a rating learned from the closes, so the expected lineup
   counts. (1.99)

## 2. The data

- **Closing lines:** ESPN's recorded pre-game closes: ESPN BET through 2024-25, DraftKings for most of
  2025-26, and ESPN's consensus line before 2023-24.
- **Injuries:** the NBA's official injury report as it stood at the end of the evening before each game.
  Reports after Dec 21, 2025 come from a research archive of the original PDFs, checked against my own
  NBA downloads.
- **Results and player minutes:** ESPN box scores, back to 2014-15.

## 3. How I tested it

I chose every setting on 2024-25, then graded 2025-26 once. To make sure one season wasn't luck, I
repeated the whole process for each of the last ten seasons, tuning on the season before each one. I
only count a gain as real if it holds in 95% of 10,000 resamples of the games.

## 4. Results

| Step (2025-26) | Off the close | Gain (95% range) | Real gain in the last 10 seasons |
|---|---|---|---|
| Starting model | 3.00 | | |
| + learn from past closing lines | 2.44 | +0.55 (0.43 to 0.67) | 10 of 10 |
| + back-to-backs | 2.21 | +0.23 (0.17 to 0.29) | 10 of 10 |
| + injury report | 2.02 | +0.19 (0.13 to 0.26) | 4 of 4 with reports to learn from |
| + box-score players | 2.00 | +0.02 (0.00 to 0.04) | 9 of 10 |
| + player ratings | **1.99** | +0.00 (-0.04 to 0.05) | 4 of 10 |

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

Before the ten-season run, I graded 2025-26 three times as I added pieces (2.14, 2.10, 2.05), each chosen
on 2024-25 first with the code frozen in git. The ten-season run is the cleaner test.

## 7. Next

Projected minutes for each player, pace for totals, and saving the injury report every night.

The full numbers are in [DETAILS.md](DETAILS.md), and every game is in [results_by_game.csv](results_by_game.csv).
