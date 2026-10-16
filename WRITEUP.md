# Pricing NBA games the night before

**The model.** Every team has a rating in points and every player a value from his box scores. The
predicted margin is the team rating gap, plus home court, plus the strength gap between the players
expected to be available, plus a back-to-back penalty and the regulars listed out on the NBA's injury
report. It walks forward one day at a time: it prices a day's games, then learns from their results and
closing lines. Nothing from game day is used; injuries come from the last report of the evening before.

**The data.**
- **Closing lines: ESPN's recorded pre-game closes.** ESPN records each book's open and close before
  tip-off and keeps in-game odds separate, so its close is a true pre-game number. That is ESPN BET through 2024-25 and DraftKings for most of 2025-26, after
  ESPN changed partners. Seasons before 2023-24 use ESPN's consensus line, the best it has for them.
- **Injuries: the NBA's official injury report** as it stood at the end of the evening before each
  game. After Dec 21, 2025 the NBA's own addresses stop working, so those reports come from a research
  archive of the original PDFs; every file matches its checksum, and the files that overlap with my own
  NBA downloads read identically.
- **Results and player minutes: ESPN box scores**, back to 2014-15.

**How I tested it.** I chose every setting on 2024-25 and graded 2025-26. Then I ran the same process
on each of the last ten seasons: tune on the season before, grade the next one once. A gain counts only
if it holds in 95% of resamples of the games.

**Results.** On 2025-26 my spreads were **1.99 points** from the pre-game close on average, down from
**3.00** for a ratings-only model. Across the ten seasons, the full model beat the ratings-only model by
0.6 to 1.1 points every year. The close is still the better forecast of the final score (10.88 points
off against my 11.13), as I would expect.

| Step (2025-26) | Off the close | Gain (95% range) | Real gain in the last 10 seasons |
|---|---|---|---|
| Ratings from results only | 3.00 | | |
| + learn from past closing lines | 2.44 | +0.55 (0.43 to 0.67) | 10 of 10 |
| + second night of a back-to-back | 2.21 | +0.23 (0.17 to 0.29) | 10 of 10 |
| + night-before injury report | 2.02 | +0.19 (0.13 to 0.26) | 4 of 4 with reports to learn from |
| + box-score player values | 2.00 | +0.02 (0.00 to 0.04) | 9 of 10 |
| + full player ratings | **1.99** | +0.00 (-0.04 to 0.05) | 4 of 10 |

Full player ratings never hurt but are inconsistent: they mattered most when the injury step had
nothing to learn from (2021-22: +0.24).

**Second numbers.** Win probability: 5.0 percentage points from the no-vig closing price, log loss
0.585 against the close's 0.570. Totals: 3.59 to **2.44 points** off the closing total, every step real.

**To be transparent.** Before the ten-season run, I graded the spread model on 2025-26 three times as
I added pieces (2.14, 2.10, 2.05), each chosen on 2024-25 first with the code frozen in git. The
ten-season run is the cleaner evidence: every season is graded with settings chosen only on earlier data.

**Next.** Projected minutes per player, pace for totals, and saving the injury report every night.
Full notes are in [DETAILS.md](DETAILS.md).
