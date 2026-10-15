# Pricing NBA games the night before

**Result.** On 2025-26, a season I never used to choose a setting, my spreads were **2.10 points**
from the pre-game closing line on average, down from **2.99** for a ratings-only model. On the 429
games where the night-before injury report exists, they were **1.92** points off. The same approach
prices totals **2.49 points** from the closing total. The close is still the better forecast of the
final score (10.88 points off against my 11.17), as I would expect.

**The model.** Every team has a rating in points and every player a value from his own box scores.
The predicted margin is the rating gap, plus home court, plus the strength gap between the players
expected to be available, plus a back-to-back penalty and the regulars listed out on the NBA injury
report. It walks forward one day at a time: it prices a day's games, then learns from their results
and closing lines. Nothing from game day is used; injuries come from the report at 8:30 PM the
evening before.

**What moved the number (points off the close, 2025-26):**

| Step | Off the close | Gain (95% range) |
|---|---|---|
| Ratings from results only | 2.99 | |
| + learn from past closing lines | 2.44 | +0.55 (0.43 to 0.67) |
| + second night of a back-to-back | 2.21 | +0.23 (0.17 to 0.29) |
| + night-before injury report | 2.14 | +0.08 (0.04 to 0.12); +0.22 where the report exists |
| + player and team ratings combined | **2.10** | +0.04 (0.02 to 0.05) |

I chose every setting on 2024-25, checked new ideas on 2023-24, and froze the code in git before
each 2025-26 run. A gain counts only if it holds in 95% of 10,000 resamples of the games.

**The data, which was most of the work.** Pinnacle's history is only sold, so I looked for free
closes. SportsbookReview's "latest" line turned out to include in-game odds: Jazz at Nuggets on
Dec 22, 2025 shows Denver -23.5 against a -12.5 pre-game close, in a game Denver won by 23. Grading
against that would leak the result, so I used ESPN's recorded pre-game closes instead (ESPN BET, then
DraftKings after ESPN switched partners mid-season), after checking they show no sign of live lines.
The NBA's injury report archive stops on Dec 21, 2025, which is why I show those games separately.

**What did not work.** Returning players, three games in four nights, rest days, time zones, blowout
caps, faster early-season learning, per-team home court and "sat out last game" all came out as
noise. The model already learns from every past closing line, and the market had priced them in.

**To be transparent.** The spread model ran on 2025-26 twice: a first version (2.14) and the final
one after adding player ratings, which I had chosen on 2024-25 and confirmed on 2023-24 first. The
totals model ran once.

**Second numbers.** Win probability: 5.2 percentage points from the no-vig closing price, log loss
0.587 against the close's 0.570. Totals: 3.59 to 2.49 points off the closing total, every step real.

**Next.** Day-before injury news for 2026, projected minutes per player, and pace for totals.
Full notes are in [DETAILS.md](DETAILS.md).
