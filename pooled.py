"""Tune on several past seasons at once instead of just the one before, then grade the next season.
Usage: python3 pooled.py

Step 1 (choose how many seasons to tune on, without touching 2025-26): grade 2024-25 three ways,
       tuned on 2023-24 only, on the 3 seasons before it, and on all 8 seasons before it.
Step 2 (the test): take the window that did best on 2024-25, move it forward one season, tune on it,
       and grade 2025-26 once.
"""
import statistics as st
from multiprocessing import Pool
from data import load, TEST
from model import tuned_models, gaps, run
from evaluate import bootstrap

SEASONS = ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24",
           "2024-25", "2025-26"]
WINDOWS = {"1 season": 1, "3 seasons": 3, "all seasons": None}


def window(target, size):
    before = SEASONS[:SEASONS.index(target)]
    return tuple(before if size is None else before[-size:])


def grade(job):
    target, name = job
    games = load()
    tuned_on = window(target, WINDOWS[name])
    models = tuned_models(games, season=tuned_on)
    g = {n: gaps(games, run(games, **p), target) for n, p in models.items()}
    return target, name, tuned_on, models, g


if __name__ == "__main__":
    with Pool(3) as pool:
        check = pool.map(grade, [("2024-25", n) for n in WINDOWS])
    print("Step 1: 2024-25, full model, points off the close")
    for target, name, tuned_on, models, g in check:
        print(f"  tuned on {name:12} ({tuned_on[0]} to {tuned_on[-1]}): {st.mean(g['+ player ratings']):.3f}")
    best = min(check, key=lambda r: st.mean(r[4]["+ player ratings"]))[1]
    print(f"  -> chosen: {best}")

    target, name, tuned_on, models, g = grade((TEST, best))
    one = next(r for r in check if r[1] == "1 season")  # for reference only
    print(f"\nStep 2: {TEST}, tuned on {tuned_on[0]} to {tuned_on[-1]}")
    print(f"  settings: {models['+ player ratings']}")
    names = list(models)
    for n in names:
        print(f"  {n:20} {st.mean(g[n]):.3f}")
    for a, b in zip(names, names[1:]):
        m, lo, hi = bootstrap(g[a], g[b])
        print(f"  {b} vs {a}: {m:+.2f} ({lo:+.2f} to {hi:+.2f})")
