"""Second worker for fetch_lines: same days, newest first. Cached days are skipped by both."""
import datetime as dt
import fetch_lines
from fetch_games import SEASONS

days = []
for season, (a, b) in SEASONS.items():
    if season >= "2021-22":
        a, b = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
        days += [a + dt.timedelta(n) for n in range((b - a).days + 1)]
fetch_lines.OUT.mkdir(parents=True, exist_ok=True)
for d in reversed(days):
    if (fetch_lines.OUT / f"{d}.json").exists():
        continue  # already downloaded (by either worker)
    fetch_lines.pull(d)
print("reverse worker done")
