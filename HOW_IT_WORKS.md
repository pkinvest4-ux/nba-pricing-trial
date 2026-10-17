# How it works

A walk through the code in the order a game gets priced. Each section names the file and function.

## 1. The idea

The goal is to price a game the night before, before any sportsbook has posted a line, and to get
as close as possible to where the market finally settles: the **closing line**. The closing line is the
answer key, not an opponent. By tip-off it has every bet and every piece of news in it, so it is the
best estimate of the game there is. Getting close to it means pricing the game the way the market
eventually will. Beating it is not the aim; a simple model that beat it would most likely be leaking
information from after the line went up.

The score that matters: **average points between my number and the closing spread**.

## 2. The data (`fetch_*.py`)

| Script | What it gets | Why |
|---|---|---|
| `fetch_games.py` | Every game and final score, 2014-15 to 2025-26, from ESPN | Results to learn from |
| `fetch_espn_odds.py` | Each book's pre-game open and close for the spread, total and moneyline, from ESPN | The answer key, and lines to learn from |
| `fetch_boxscores.py` | Every player's minutes and Game Score in every game | Player values and lineups |
| `fetch_injuries.py` | The NBA's official injury report as it stood at the end of the evening before each game | Who is out tomorrow |

Everything is cached in `data/`, so it only downloads once.

## 3. What is known the night before (`data.py`)

`load()` reads the files and adds these to every game. Each function processes a day's games first
and only then adds that day's results to what it knows, so no game ever sees its own outcome.

- **`add_lines`: the answer key.** One book's pre-game close per season, as ESPN recorded it: ESPN BET,
  then DraftKings once ESPN switched partners mid-2025-26. ESPN keeps in-game odds separate, so this is
  a genuine pre-game number. `no_vig` turns the closing moneyline into a fair win probability by
  removing the book's margin (both sides' implied odds add up to a bit over 100%).
- **`add_back_to_backs`.** Is a team playing the second night in a row? The schedule is public months
  ahead, so this is always fair to use.
- **Player values (`rate`).** A player's value is his Game Score per minute minus a bench player's
  (0.15), times the minutes he usually plays. Game Score is a standard one-number summary of a box-score
  line (points, rebounds, assists, steals, blocks, minus missed shots, turnovers and fouls). A player
  with only a few games is pulled toward a typical value, as if he had already played 60 average minutes.
- **`add_injuries`.** For each regular listed Out (full value), Doubtful (75%) or Questionable (30%) on
  the night-before report, the team loses his value. Only regulars count: 16+ minutes a game in the
  team's recent games, and still on the team. A team's total is capped at 40, so a night where a team
  rests its whole rotation can't swamp the scale.
- **`add_roster`.** The total value of the players who have been playing for the team lately, with
  minutes scaled to the 240 a team actually plays.
- **`add_lineups`.** The expected lineup: recent players, minus anyone listed Out or Doubtful,
  Questionable players at 70% of their minutes. Also who actually played, which the model only learns
  from after the game.

## 4. Pricing a day, then learning (`model.py`, `run`)

`run` walks through every season one day at a time.

**Step 1, price the day.** For each game, the predicted home margin is the sum of six parts:

| Part | What it is | Final setting |
|---|---|---|
| Team ratings | Home rating minus away rating, in points | learned |
| Home court | Same for every home team | 2.0 points |
| Back-to-back | Points the tired team gives up | 2.0 points |
| Injuries | Gap in missing value x a weight | 0.1 |
| Box-score players | Gap in available players' value x a weight | 0.05 |
| Player ratings | Gap between the expected lineups, each player in points per 48 minutes | weight 0.75 |

**Step 2, learn from the day.** Only after every game on the day is priced:
- Each team's rating moves toward the actual result: by 1% of how far off we were (`k`).
- Each team's rating also moves toward the closing line: by 10% of the gap (`k_market`). This is the
  biggest single improvement. The market knows things a box score doesn't, like injuries and rest, so
  learning from its past closes keeps the ratings honest.
- Each player's rating moves the same way, shared among the players who actually played, by minutes.
  Players learn almost entirely from the closing line (`p_mkt` 0.015) and barely from results (`p_k`
  0.001); results alone are too noisy to separate one player from his teammates.

**At the start of each season,** team ratings keep 70% of their value (`carry`), because rosters change.
Player ratings carry over in full (`p_carry` 1.0), since a player is the same player after the summer.

## 5. Choosing the settings (`model.py`, `tuned_models`)

The model is built one step at a time. For each step, every setting in a small grid is tried on the
**tuning season** (2024-25), and the one closest to the close is kept. Then the next step is added on
top. Building it in steps means each step's contribution can be measured on its own.

The **test season** (2025-26) is never used to choose anything. It is only graded.

## 6. Grading (`evaluate.py`)

- **Points off the close** for every step, on the season being graded (`gaps`).
- **Is a gain real? (`bootstrap`)** The two models are compared on the same games. Then the games are
  resampled 10,000 times (drawn at random with replacement) and the gain recomputed each time. If the
  middle 95% of those gains is entirely above zero, the gain is real, not luck.
- **Against the real result.** The model and the close are both compared with the final margin. The
  close should win, slightly. It does.
- **Win probability.** Actual margins land around the prediction in a bell curve about 13 points wide,
  so a margin turns into a win probability. It is graded against the no-vig closing price, using log
  loss (lower is better; it punishes being confidently wrong).

## 7. Ten seasons (`walkforward.py`)

The same process, repeated: for each season from 2016-17 to 2025-26, choose every setting on the
season before, then grade that season once. One test season can be lucky; ten in a row can't. Seasons
before 2023-24 are graded against ESPN's consensus line, because ESPN has no labelled close for them.

## 8. Totals (`totals.py`)

Each team gets an offence rating (points it scores above average) and a defence rating (points it
allows above average), around a league scoring level that drifts over time. Expected points for each
team come from its offence against the other team's defence; the total is the sum. It learns from
results and past closing totals the same way, and adjusts for back-to-backs (tired teams score about
half a point less) and injuries (a team missing regulars scores less).

## 9. One game, start to finish (`explain.py`)

```
python3 explain.py WSH DET 2025-11-10
```

prints each of the six parts for Wizards at Pistons, the model's number, the close and the result,
plus both expected lineups with each player's minutes and rating.

## 10. The spreadsheets (`export_results.py`)

Writes `results_by_game.csv`, one row per game of 2024-25 and 2025-26: the six parts of the number, the
model's number, the close and the result, how far apart they were, and the same for the total. Sort by
"points off the close" to see the biggest misses. `results_summary.csv` has one row per season.

## 11. Experiments that did not make the final model

- **`pooled.py`** tunes on several past seasons at once instead of just the one before. Older seasons
  pulled home court up and the back-to-back penalty down, toward an older NBA, and it did worse.
- **`player_values.py`** values a missing player by plus-minus, points, win shares or BPM instead of
  Game Score. None beat Game Score on the tuning season.

The numbers are in [DETAILS.md](DETAILS.md).
