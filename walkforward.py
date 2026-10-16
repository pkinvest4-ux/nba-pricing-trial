"""Walk-forward test: for each season, choose every setting on the season before it, then grade that
season once. Shows whether the model's design holds up year after year, not just in one season.
Usage: python3 walkforward.py [first season] (default 2016-17). Runs seasons in parallel."""
import sys, statistics as st, collections
from multiprocessing import Pool
from data import load
from model import tuned_models, gaps, run
from evaluate import bootstrap

SEASONS = ["2015-16", "2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23",
           "2023-24", "2024-25", "2025-26"]


def one(target):
    games = load()
    prev = SEASONS[SEASONS.index(target) - 1]
    models = tuned_models(games, season=prev)
    names = list(models)
    g = {n: gaps(games, run(games, **p), target) for n, p in models.items()}
    steps = []
    for a, b in zip(names, names[1:]):
        m, lo, hi = bootstrap(g[a], g[b], n=4000)
        steps.append((b, m, lo, hi))
    src = collections.Counter(x["key_book"] for x in games if x["season"] == target and x["close"] is not None)
    return target, prev, len(g["baseline"]), dict(src), {n: st.mean(v) for n, v in g.items()}, steps


if __name__ == "__main__":
    first = sys.argv[1] if len(sys.argv) > 1 else "2016-17"
    targets = SEASONS[SEASONS.index(first):]
    with Pool(min(len(targets), 8)) as pool:
        results = pool.map(one, targets)
    names = list(results[0][4])
    print(f"\n{'season':8} {'tuned on':8} {'games':>5}  " + "  ".join(f"{n[:13]:>13}" for n in names) + "   graded against")
    for target, prev, n, src, means, steps in results:
        print(f"{target:8} {prev:8} {n:5}  " + "  ".join(f"{means[k]:13.2f}" for k in names)
              + "   " + ", ".join(f"{k} {v}" for k, v in src.items()))
    print("\nwhich steps were real gains (95% range above zero), by season:")
    for target, prev, n, src, means, steps in results:
        print(f"  {target}: " + "  ".join(f"{b.replace('+ ', '')} {m:+.2f}{'*' if lo > 0 else ''}" for b, m, lo, hi in steps))
    print("  (* = real gain)")
