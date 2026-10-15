# Pricing NBA games the night before: how close to the close?

**Result:** on the 2025-26 season (1,230 games, never used to choose anything), my spreads were
**2.14 points** from the pre-game closing line on average, down from **2.99** for a ratings-only
model. On the 429 games where the night-before injury report exists, they were **1.92** points off.
Every improvement holds up on that unseen season. The close is still the better forecast of the
final score, which is what I would expect.

## What the model knows, and when

Every team has a rating in points. Predicted home margin = home rating minus away rating, plus
home-court advantage, plus two things known the night before: a team playing the second night of a
back-to-back, and regulars listed Out, Doubtful or Questionable on the NBA's injury report.

It walks through seasons one day at a time. It prices every game on a day first, then learns from
that day's results and closing lines. Nothing from game day is used: the injury information is the
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
- Other fixes: a sanity rule drops "spreads" over 30 points (ESPN once stored prices like -110 in that
  field), All-Star and exhibition games are removed, and traded players stop counting for their old
  team's injuries.

## How I tested it

I chose every setting on 2024-25 and froze the code in git (commit `dedd7fd`) before running
2025-26 once. Each gain is checked by comparing two models on the same games and resampling those
games 10,000 times: if the gain shows up in 95% of resamples, it is not luck.

## Results on 2025-26

| Model | Points off the close (1,230 games) | With injury report (429 games) |
|---|---|---|
| Ratings from results only | 2.99 | 2.88 |
| + learn from past closing lines | 2.44 | 2.42 |
| + second night of a back-to-back | 2.21 | 2.15 |
| + night-before injury report | **2.14** | **1.92** |

- **Past closes:** +0.55 points (95% range 0.43 to 0.67). The market knows things a box score does not.
- **Back-to-backs:** worth about 2 points to the rested team. +0.23 points (0.17 to 0.29).
- **Injuries:** +0.22 points where the report exists (0.11 to 0.34). Only +0.08 over the full season,
  because the NBA's report archive stops on Dec 21, 2025, so later games get no injury adjustment.
- **Against the final score:** the close misses by 10.88 points on average, my model by 11.17. On the
  injury-report games the gap is only 0.12 points and not statistically clear.

**Win probability**, as a second number: turning each margin into a probability (margins vary about
13 points around the prediction), mine were 5.3 percentage points from the no-vig closing price on
average. Log loss: mine 0.586, the close 0.570, a coin flip 0.693. Calibration is good in the middle
(when I said 60 to 80%, the home team won 74%) and a little overconfident at the extremes.

## What did not work

"Regulars who sat out the previous game" from box scores, which exists for every game, added nothing
on 2024-25. Yesterday's closing line, which the ratings already learn from, had priced that absence
in. The injury report adds value because it says who is out tomorrow.

## What I would do next

Find day-before injury news for 2026 (another archive, or saving the report each night going
forward), rate players rather than teams, and soften the extremes of the win probability.
