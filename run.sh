#!/bin/sh
# Download (cached after the first run), then grade. Add --test to grade the 2025-26 test season.
set -e
cd "$(dirname "$0")"
[ -f data/games.jsonl ] || python3 fetch_games.py
[ -f data/espn_odds.json ] || python3 fetch_espn_odds.py
[ -f data/boxscores.json ] || python3 fetch_boxscores.py
[ -f data/injuries.json ] || python3 fetch_injuries.py
python3 evaluate.py "$@"
echo
python3 totals.py "$@"
