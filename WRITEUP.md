# Pricing NBA games the night before

**Result.** On 2025-26 my spreads were **1.99 points** from the pre-game closing line on average,
down from **3.00** for a ratings-only model, with every setting chosen on 2024-25. Run the same way on
each of the last ten seasons (tune on the season before, grade once), the full model beat the
ratings-only model by 0.6 to 1.1 points every year. Totals: **2.44 points** from the closing total.
The close is still the better forecast of the final score (10.88 points off against my 11.13).

**The model.** Every team has a rating in points and every player a value from his box scores. The
predicted margin is the team rating gap, plus home court, plus the strength gap between the players
expected to be available, plus a back-to-back penalty and the regulars listed out on the NBA's injury
report. It walks forward one day at a time: it prices a day's games, then learns from their results and
closing lines. Nothing from game day is used; injuries come from the last report of the evening before.

**What moved the number, 2025-26 (and in how many of the last 10 seasons it was a real gain):**

| Step | Off the close | Gain (95% range) | Real gain in |
|---|---|---|---|
| Ratings from results only | 3.00 | | |
| + learn from past closing lines | 2.44 | +0.55 (0.43 to 0.67) | 10 of 10 |
| + second night of a back-to-back | 2.21 | +0.23 (0.17 to 0.29) | 10 of 10 |
| + night-before injury report | 2.02 | +0.19 (0.13 to 0.26) | 4 of 4 with reports to learn from |
| + box-score player values | 2.00 | +0.02 (0.00 to 0.04) | 9 of 10 |
| + full player ratings | **1.99** | +0.00 (-0.04 to 0.05) | 4 of 10 |

A gain counts only if it holds in 95% of resamples of the games. Full player ratings never hurt but
are inconsistent: they mattered most when the injury step had nothing to learn from (2021-22: +0.24).

**The data, which was most of the work.**
- Pinnacle's history is only sold. SportsbookReview's "latest" line turned out to include in-game odds
  (Jazz at Nuggets, Dec 22, 2025: Denver -23.5 against a -12.5 pre-game close; Denver won by 23), so I
  graded against ESPN's recorded pre-game closes: ESPN BET, then DraftKings after ESPN changed partners.
  ESPN has Pinnacle only for 2015-16; seasons before 2023-24 are graded against ESPN's consensus line.
- The NBA's injury report addresses stop working after Dec 21, 2025 (it switched to quarter-hour files).
  I filled the gap from a research archive of the original PDFs, after checking every file against its
  checksum and that the 30 files overlapping my own NBA downloads parse identically.
- A download silently dropped most of two seasons; the script now fails loudly instead.

**What did not work.** Returning players, three games in four nights, rest days, time zones, blowout
caps, faster early-season learning and per-team home court were all noise. The model already learns
from every past closing line, and the market had priced them in.

**To be transparent.** Before the ten-season run, I graded the spread model on 2025-26 three times as
I added pieces (2.14, 2.10, 2.05), each chosen on 2024-25 first with the code frozen in git. The
walk-forward is the cleaner evidence: every season is graded with settings chosen only on earlier data.

**Second numbers.** Win probability: 5.0 percentage points from the no-vig closing price, log loss
0.585 against the close's 0.570. Totals: 3.59 to 2.44 points off the closing total, every step real.

**Next.** Projected minutes per player, pace for totals, and saving the injury report every night.
Full notes are in [DETAILS.md](DETAILS.md).
