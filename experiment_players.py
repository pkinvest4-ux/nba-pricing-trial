"""Full player ratings vs the current final model. Chosen on 2024-25, confirmed on 2023-24.
2025-26 is not touched here."""
import statistics as st, time
import model

games = model.load()
current = model.tuned_models(games)["+ player ratings"]
gap = lambda p, s: model.gaps(games, model.run(games, **p), s)
t0 = time.time(); cur_t = gap(current, model.TUNE); print(f"current final model, 2024-25: {st.mean(cur_t):.3f} ({time.time()-t0:.0f}s per run)")

p = dict(current, roster=0.0, p_w=1.0, p_mkt=0.0, p_carry=0.8)
def pick(key, values):
    global p
    res = [(st.mean(gap(dict(p, **{key: v}), model.TUNE)), v) for v in values]
    best = min(res)
    p = dict(p, **{key: best[1]})
    print(f"  {key}: " + "  ".join(f"{v}={sc:.3f}" for sc, v in sorted(res, key=lambda x: str(x[1]))) + f"  -> {best[1]}")
pick("p_k", (0.002, 0.005, 0.01, 0.02, 0.04))
pick("p_mkt", (0.0, 0.002, 0.005, 0.01, 0.02))
pick("p_carry", (0.5, 0.7, 0.85, 1.0))
pick("p_w", (0.5, 0.75, 1.0, 1.25))
pick("k", (0.005, 0.01, 0.02, 0.03))
pick("k_market", (0.1, 0.15, 0.2, 0.3))
pick("p_k", (0.002, 0.005, 0.01, 0.02, 0.04))
pick("roster", (0.0, 0.02, 0.05))
pick("inj", (0.0, 0.05, 0.1, 0.15))
new_t = gap(p, model.TUNE)
m, lo, hi = model.bootstrap(cur_t, new_t)
vm, vlo, vhi = model.bootstrap(gap(current, "2023-24"), gap(p, "2023-24"))
print(f"\nfull player ratings: {p}")
print(f"2024-25: {st.mean(cur_t):.3f} -> {st.mean(new_t):.3f}, gain {m:+.3f} ({lo:+.3f} to {hi:+.3f})")
print(f"2023-24: gain {vm:+.3f} ({vlo:+.3f} to {vhi:+.3f})")
