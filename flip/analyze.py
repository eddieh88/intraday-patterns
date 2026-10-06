"""Verdicts for prereg/silent_flip.md.

  python3 flip/analyze.py            development
  python3 flip/analyze.py holdout    the holdout, once (primary only, t >= 1.65)
"""
import sys

import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("flip")
import sim
from flip_stats import clustered, clustered_diff, spec_mask, net, BP

PERIOD = sys.argv[1] if len(sys.argv) > 1 else "dev"
DEV = PERIOD == "dev"
T_CRIT = 2.0 if DEV else 1.65
T_CRIT_Q2 = 2.75 if DEV else 2.26          # Amendment 2: Q2 standard errors are ~1.37x too small
Q3_BIAS = 0.04                                # Amendment 2: Q3 is biased against the setup by ~0.04R

T = pd.read_parquet(f"cache/flip_{PERIOD}.parquet")
T["block"] = np.minimum(T.date.dt.year, 2024)


def q_stats(x):
    """(Q1, Q2, Q3) as (mean, se, t) for one specification's rows."""
    real, fake = x[x.kind == "real"], x[x.kind == "fake"]
    q1 = clustered(net(real), real.date)[:3]
    q2 = clustered_diff(net(real), real.date, net(fake), fake.date)
    q3 = clustered(net(real) - net(real, "R_rand", "c_rand"), real.date)[:3]
    return q1, q2, q3


P = T[spec_mask(T, sim.PRIMARY)]
real = P[P.kind == "real"]
print(f"{PERIOD}: primary spec, {len(real):,} real trades on {real.date.nunique()} sessions "
      f"({real.symbol.nunique()} names); {(P.kind == 'fake').sum():,} fake-level trades")
print(f"net R at {BP} bp, session-clustered; critical t {T_CRIT} (Q2: {T_CRIT_Q2})\n")

prim = q_stats(P)
blocks = {b: q_stats(g) for b, g in P.groupby("block")} if DEV else {}
grid = [q_stats(T[spec_mask(T, sp)]) for sp in sim.GRID] if DEV else []
names = ("Q1 pays          real", "Q2 levels matter real - fake", "Q3 timing        real - random")
for q, name in enumerate(names):
    m, se, t = prim[q]
    ok = m > 0 and t >= (T_CRIT_Q2 if q == 1 else T_CRIT)
    line = f"  {name:32s} {m:+.4f} ± {se:.4f}  t {t:+5.2f}"
    if DEV:
        pos_b = sum(v[q][0] > 0 for v in blocks.values())
        pos_g = sum(g[q][0] > 0 for g in grid if np.isfinite(g[q][0]))
        n_g = sum(np.isfinite(g[q][0]) for g in grid)
        ok = ok and pos_b >= 3 and pos_g >= 2 / 3 * n_g
        line += f"  years +{pos_b}/4  grid +{pos_g}/{n_g}"
        line += "\n" + " " * 36 + "  ".join(f"{b}:{v[q][0]:+.4f}" for b, v in blocks.items())
    if q == 2:
        line += f"\n{'':36s}bias-corrected (+{Q3_BIAS}): {m + Q3_BIAS:+.4f}, t {(m + Q3_BIAS) / se:+.2f}  (no verdict)"
    print(f"{line}\n{'':36s}{'PASS' if ok else 'fail'}\n")

print("REPORTED, NO VERDICT  (primary spec, real trades)\n")
nr = net(real)
rep = {
    "trades": len(real), "win rate": (real.out == 1).mean(), "stopped": (real.out == 0).mean(),
    "to the close": (real.out == 2).mean(), "median target, R": real.tgt_R.median(),
    "gross R": real.R.mean(), "net R 1bp": net(real, bp=1).mean(), "net R 6bp": net(real, bp=6).mean(),
    "net R, entry to 11:00": net(real, "R_late", "c_late").mean(),
    "net R, his trailing stop": (real.R_trail - BP * real.cost).mean(),
    "setups per name per month": len(real) / real.symbol.nunique() / max(1, real.date.dt.to_period('M').nunique()),
}
for k, v in rep.items():
    print(f"  {k:28s} {v:,.4f}" if isinstance(v, float) else f"  {k:28s} {v:,}")
print()
for col in ("level", "side"):
    print(real.assign(net=nr).groupby(col).net.agg(["size", "mean"]).round(4).to_string(), "\n")
if DEV:
    print(real.assign(net=nr).groupby(real.date.dt.year).net.agg(["size", "mean"]).round(4).to_string(), "\n")

# one trade per day across the universe: the first fill, ties at random (Amendment 1)
rng = np.random.default_rng(sim.SEED)
day = real.assign(net=nr, u=rng.random(len(real))).sort_values(["date", "fill_t", "u"]).groupby("date").head(1)
m, se, t, n = clustered(day.net, day.date)
print(f"  one per day: {n} days with a trade, mean {m:+.4f} R/day, t {t:+.2f}, positive {(day.net > 0).mean():.1%}")

if DEV:
    print("\nGRID (Q1 net R, real) by spec:")
    g = pd.DataFrame([dict(strong=sp.strong, body=sp.body, tol=sp.tol, target=sp.target, q1=r[0][0], q2=r[1][0], q3=r[2][0])
                      for sp, r in zip(sim.GRID, grid)])
    print(g.pivot_table(index=["strong", "body"], columns=["target", "tol"], values="q1").round(3).to_string())
