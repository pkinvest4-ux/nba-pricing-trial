"""Try each new idea on top of the current model. Settings are chosen on 2024-25 (TUNE); each idea is
also checked on 2023-24 (VALID) where the data allows. 2025-26 is never touched here."""
import statistics as st
import model

VALID = "2023-24"
games = model.load()
best = model.tuned_models(games)["+ injuries"]
IDEAS = [  # (name, setting, values to try, needs injury reports?)
    ("returning players", "ret", (0.05, 0.1, 0.15, 0.2, 0.3, 0.4), True),
    ("three games in four nights", "three", (0.5, 1.0, 1.5, 2.0, 3.0), False),
    ("rest-day difference", "rest", (0.25, 0.5, 0.75, 1.0, 1.5), False),
    ("time zones crossed", "tz", (0.25, 0.5, 0.75, 1.0), False),
    ("cap blowout margins", "mov_cap", (12, 15, 18, 22, 26, 30), False),
    ("learn faster early", "early", (0.25, 0.5, 1.0, 1.5, 2.0), False),
]


def gap(params, season):
    return model.gaps(games, model.run(games, **params), season)


current = gap(best, model.TUNE)
print(f"starting point: {st.mean(current):.3f} on {model.TUNE}")
for name, key, values, needs_reports in IDEAS:
    score, v = min((st.mean(gap(dict(best, **{key: x}), model.TUNE)), x) for x in values)
    trial = dict(best, **{key: v})
    new = gap(trial, model.TUNE)
    m, lo, hi = model.bootstrap(current, new)
    if needs_reports:
        valid_txt, valid_ok = "n/a (no injury reports in 2023-24)", True
    else:
        vm, vlo, vhi = model.bootstrap(gap(best, VALID), gap(trial, VALID))
        valid_txt, valid_ok = f"{vm:+.3f} ({vlo:+.3f} to {vhi:+.3f})", vm >= 0
    keep = lo > 0 and valid_ok
    print(f"{name:28} best {key}={v}: tune {m:+.3f} ({lo:+.3f} to {hi:+.3f}) | 2023-24 {valid_txt} -> {'KEEP' if keep else 'drop'}")
    if keep:
        best, current = trial, new
print("\nfinal settings:", best)
print(f"tune gap {st.mean(current):.3f}")
