"""The pre-data check in prereg/retest.md: on driftless random walks, where levels
mean nothing, real and fake bounce_12 must both sit within 2 SE of zero and of
each other. Uses retest/detect.py unchanged.

  python3 retest/random_walk_check.py
"""
import numpy as np, sys
from paths import add_to_path
add_to_path("retest")
import detect as D

rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 11)
SUB = int(sys.argv[1]) if len(sys.argv) > 1 else 10
PRE, RTH, DAYS = 66, 78, 16       # substeps per bar; bars pre-market / regular; days per path
SIG = 0.0025 / np.sqrt(SUB)                 # per-substep vol: ~0.25% per 5-min bar in regular hours

def day(p0, pre=False):
    n = PRE if pre else RTH
    steps = rng.normal(0, SIG * (0.35 if pre else 1.0), (n, SUB))
    path = p0 * np.exp(np.cumsum(steps.ravel())).reshape(n, SUB)
    o = np.concatenate([[p0], path[:-1, -1]])
    h = np.maximum(path.max(1), o); l = np.minimum(path.min(1), o); c = path[:, -1]
    return o, h, l, c

rows = {k: {"real": [], "fake": []} for k in ("a12", "b12")}
for sim in range(int(sys.argv[2]) if len(sys.argv) > 2 else 1500):
    p, rng_hist, hi_lo = 100.0, [], []
    for d in range(DAYS):
        _, ph, pl, pc = day(p, pre=True)
        o, h, l, c = day(pc[-1])
        if d < DAYS - 1:
            rng_hist.append(h.max() - l.min()); hi_lo.append((h.max(), l.min())); p = c[-1] * np.exp(rng.normal(0, 0.005))
    atr = np.mean(rng_hist[-14:])
    (pdh, pdl), (p2h, p2l) = hi_lo[-1], hi_lo[-2]
    hours = 9.5 + np.arange(RTH) * 5 / 60
    real, fake = D.levels(pdh, pdl, p2h, p2l, ph.max(), pl.min(), o[0])
    for kind, lv in (("real", real), ("fake", fake)):
        for _, L in lv:
            _, r = D.scan(o, h, l, c, hours, pc[-1], L, atr)
            if r:
                for k in rows: rows[k][kind].append(r[k])

print(f"random walk, {SUB} steps per bar: levels mean nothing, so every mean below should be ~0")
ok = True
for k, label in (("a12", "PRIMARY, from the touch bar's close"), ("b12", "from the level price")):
    R = rows[k]; print(f"  {k}  {label}")
    for kind, v in R.items():
        v = np.array(v); se = v.std(ddof=1) / np.sqrt(len(v))
        print(f"    {kind}: {len(v):6d} retests   mean {v.mean():+.4f}   SE {se:.4f}   t {v.mean()/se:+.2f}")
    a, b = np.array(R["real"]), np.array(R["fake"])
    t = (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
    print(f"    real - fake: {a.mean()-b.mean():+.4f}  t {t:+.2f}")
    if k == "a12":
        ok = all(abs(v.mean()) < 2 * v.std(ddof=1) / np.sqrt(len(v)) for v in (a, b)) and abs(t) < 2
print(f"\n{'PASS -- the primary outcome shows no mechanical bounce' if ok else 'FAIL -- the primary outcome is biased'}")
sys.exit(0 if ok else 1)
