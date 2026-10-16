"""Grade the spread model. Run:  python3 evaluate.py          (the tuning season, 2024-25)
                                python3 evaluate.py --test   (the test season, 2025-26)

For each step of the model: average points between our number and the closing line, and whether the
step's gain is real. "Real" means the gain still shows up in 95% of 10,000 resamples of the games
(the bootstrap). Also compares the final model with the close against the actual results, and turns
the margin into a win probability graded against the closing moneyline.
"""
import math
import random
import statistics as st
import sys
from data import load, TUNE, TEST
from model import run, gaps, tuned_models


def bootstrap(a, b, n=10000, seed=7):
    """Average of (a - b) over games, with a 95% range: resample the games with replacement
    10,000 times and take the middle 95% of the averages."""
    rnd, d = random.Random(seed), [x - y for x, y in zip(a, b)]
    means = sorted(st.mean(rnd.choices(d, k=len(d))) for _ in range(n))
    return st.mean(d), means[int(0.025 * n)], means[int(0.975 * n)]


def report(games, models, season, only=None, label=""):
    preds = {n: run(games, **p) for n, p in models.items()}
    names = list(models)
    for line in ("close", "open"):
        g = {n: gaps(games, pr, season, line, only) for n, pr in preds.items()}
        books = sorted({x["key_book"] for x in games if x["season"] == season and x["key_book"]})
        print(f"\n{season}{label} vs the {' / '.join(books)} {line.upper()} ({len(g['baseline'])} games): average points off")
        for n in names:
            print(f"  {n:16} {st.mean(g[n]):.2f}")
        for a, b in zip(names, names[1:]):
            m, lo, hi = bootstrap(g[a], g[b])
            verdict = "real" if lo > 0 else ("worse" if hi < 0 else "could be noise")
            print(f"  {b} vs {a}: {m:+.2f} points, 95% range {lo:+.2f} to {hi:+.2f} ({verdict})")
    best = preds[names[-1]]
    rows = [(abs(g["margin"] - p), abs(g["margin"] + g["close"])) for g, p in zip(games, best)
            if g["season"] == season and g["close"] is not None and (only is None or only(g))]
    m, lo, hi = bootstrap([r[0] for r in rows], [r[1] for r in rows])
    print(f"\n  vs the real final margin: model misses by {st.mean(r[0] for r in rows):.2f}, "
          f"the close by {st.mean(r[1] for r in rows):.2f} (close better by {m:.2f}, {lo:.2f} to {hi:.2f})")
    return preds


def win_probability(games, preds, season):
    """Margin -> win probability: actual margins scatter around our prediction in a bell curve, whose
    width is measured on seasons before the tuning season. Graded against the no-vig closing price."""
    sigma = st.pstdev([g["margin"] - p for g, p in zip(games, preds) if g["season"] < TUNE])
    rows = [(0.5 * (1 + math.erf(p / (sigma * math.sqrt(2)))), g["close_prob"], g["margin"] > 0)
            for g, p in zip(games, preds) if g["season"] == season and g["close_prob"] is not None]
    log_loss = lambda p, won: -math.log(min(max(p if won else 1 - p, 1e-6), 1))
    ours, book = [log_loss(p, w) for p, _, w in rows], [log_loss(b, w) for _, b, w in rows]
    m, lo, hi = bootstrap(ours, book)
    print(f"\n{season} win probability ({len(rows)} games, bell-curve width {sigma:.1f} points)")
    print(f"  average gap to the no-vig close: {st.mean(abs(p - b) for p, b, _ in rows) * 100:.1f} points")
    print(f"  log loss: model {st.mean(ours):.4f}, closing price {st.mean(book):.4f}, coin flip {math.log(2):.4f}"
          f"  (close better by {m:.4f}, {lo:.4f} to {hi:.4f})")
    for low in (0.0, 0.2, 0.4, 0.6, 0.8):
        b = [w for p, _, w in rows if low <= p < low + 0.2]
        if b:
            print(f"    model said {low:.0%} to {low + 0.2:.0%}: home won {st.mean(b):.0%} of {len(b)}")


if __name__ == "__main__":
    season = TEST if "--test" in sys.argv else TUNE
    games = load()
    models = tuned_models(games)
    for n, p in models.items():
        print(f"{n:16} {p}")
    preds = report(games, models, season)
    win_probability(games, preds[list(models)[-1]], season)
    if season == TEST:  # the injury step can only be judged where a night-before report exists
        print("\n" + "=" * 70)
        report(games, models, season, only=lambda g: g["has_report"], label=" (games with an injury report)")
