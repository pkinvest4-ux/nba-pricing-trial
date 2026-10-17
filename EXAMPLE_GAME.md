# One game, start to finish

**Washington Wizards at Detroit Pistons, November 10, 2025.** This is how the final model built its
number the night before. Positive numbers favour Detroit. Made with `python3 explain.py WSH DET 2025-11-10`.

| Part | What it says | Points |
|---|---|---|
| Team ratings | Detroit +2.5, Washington -7.7 | **+10.2** |
| Home court | Detroit at home | **+2.0** |
| Back-to-back | Detroit played the night before | **-2.0** |
| Injury report | Detroit missing 9.8 in value, Washington 3.1 | **-0.7** |
| Box-score players | Detroit's available players are slightly stronger | **+0.6** |
| Player ratings | Detroit's expected lineup rates higher | **+1.0** |
| **Model** | | **Detroit by 11.2** |
| **Close (ESPN BET)** | | **Detroit by 10.5** |
| **Result** | | **Detroit by 2** |

The model was 0.7 points from the close. The game itself finished 8.5 points from both, which is why
the close is the answer key and not the score: one game's result is mostly noise.

## Expected lineups

Each player's expected minutes, and his player rating: the points per 48 minutes he adds over an
average player.

| Detroit | Min | Rating | | Washington | Min | Rating |
|---|---|---|---|---|---|---|
| Cade Cunningham | 40 | +0.9 | | Kyshawn George | 24 | -0.3 |
| Duncan Robinson | 35 | -0.3 | | Alex Sarr | 23 | -0.6 |
| Ausar Thompson | 32 | +0.3 | | CJ McCollum | 23 | +1.2 |
| Jalen Duren | 31 | +0.2 | | Bub Carrington | 23 | -0.6 |
| Ronald Holland II | 26 | +0.4 | | Tre Johnson | 21 | -0.1 |
| Caris LeVert | 21 | +0.6 | | Khris Middleton | 19 | +1.6 |
| Javonte Green | 21 | -0.4 | | Corey Kispert | 16 | -1.1 |
| Paul Reed | 11 | -0.7 | | Justin Champagnie | 14 | -0.2 |
| Chaz Lanier | 8 | 0.0 | | AJ Johnson | 13 | -0.2 |

Top nine shown for each team. Washington's minutes are spread across more players.
