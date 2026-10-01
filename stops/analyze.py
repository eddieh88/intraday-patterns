"""Verdicts for prereg/structure_stops.md.

  python3 stops/analyze.py            development
  python3 stops/analyze.py holdout    the holdout, once (thresholds t >= 1.65)
"""
import sys

import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("stops")
import sim
from stats import clustered, net, cell

PERIOD = sys.argv[1] if len(sys.argv) > 1 else "dev"
T_CRIT = 2.50 if PERIOD == "dev" else 1.65
BP = 3
P = cell(sim.PRIMARY_B, sim.PRIMARY_T)
CELLS = [cell(b, k) for b in sim.BUFFERS for k in sim.TARGETS]

T = pd.read_parquet(f"cache/stops_{PERIOD}.parquet")
T["block"] = np.minimum(T.date.dt.year, 2024)          # 2024 carries 2025 Q1
RW = pd.read_parquet("cache/stops_random_walk_sub60.parquet")


def verdict(x, stat):
    """stat(frame, cell) -> per-trade series. Applies the prereg's three conditions."""
    m, se, t, n = clustered(stat(x, P), x.date)
    blocks = {b: stat(g, P).mean() for b, g in x.groupby("block")}
    cells = {c: stat(x, c).mean() for c in CELLS}
    c1 = m > 0 and t >= T_CRIT
    if PERIOD != "dev":
        return m, se, t, n, blocks, cells, c1
    c2 = sum(v > 0 for v in blocks.values()) >= 3
    c3 = all(v > 0 for v in cells.values())
    return m, se, t, n, blocks, cells, c1 and c2 and c3


def show(name, res):
    m, se, t, n, blocks, cells, ok = res
    bl = "  ".join(f"{b}:{v:+.4f}" for b, v in blocks.items())
    worst = min(cells, key=cells.get)
    print(f"  {name:28s} {m:+.4f} ± {se:.4f}  t {t:+5.2f}  n {n:7,}  {'PASS' if ok else 'fail'}")
    print(f"  {'':28s} by year  {bl}")
    print(f"  {'':28s} cells >0: {sum(v > 0 for v in cells.values())}/6, lowest {worst} {cells[worst]:+.4f}")


Q1 = lambda x, c: net(x, f"S_{c}", BP) - net(x, f"C_{c}", BP)
Q2 = lambda x, c: net(x, f"S_{c}", BP)
Q3 = lambda x, c: net(x, f"S_{c}", BP) - net(x, f"M_{c}", BP)

print(f"{PERIOD}: {len(T):,} trades, {T.date.nunique()} sessions, {T.date.min().date()} to {T.date.max().date()}")
print(f"net R at {BP}bp, session-clustered; critical t {T_CRIT}\n")
for s in sim.SETUPS:
    x = T[T.setup == s]
    print(f"{s}  ({len(x):,} entries; S valid in primary cell: {x[f'R_S_{P}'].notna().sum():,})")
    show("Q1 placement  S - C", verdict(x, Q1))
    show("Q2 pays       S", verdict(x, Q2))
    if s != "ORB":
        show("Q3 vs momentum  S - M", verdict(x[x[f"R_M_{P}"].notna()], Q3))
    print()

print("REPORTED, NO VERDICT  (primary cell unless named)\n")
rows = []
for s in sim.SETUPS:
    x = T[T.setup == s]; r = RW[RW.setup == s]
    o = x[f"o_S_{P}"]
    tf = x[f"R_S_{P}"].where(o != 3, sim.PRIMARY_T) - BP * x[f"c_S_{P}"]
    rows.append(dict(
        setup=s,
        S_gross=x[f"R_S_{P}"].mean(), S_3bp=Q2(x, P).mean(), S_6bp=net(x, f"S_{P}", 6).mean(),
        S_tgt_first=tf.mean(), RW_S_gross=r[f"R_S_{P}"].mean(),
        C_3bp=net(x, f"C_{P}", BP).mean(), V_3bp=net(x, f"V_{sim.PRIMARY_T}", BP).mean(),
        LT_3bp=net(x, "LT", BP).mean(),
        ORBmid_3bp=net(x, "ORBmid", BP).mean() if s == "ORB" else np.nan,
        win=(o == 1).mean(), stop=o.isin([0, 3]).mean(), both=(o == 3).mean(), time=(o == 2).mean(),
        width_bp=x[f"bp_{sim.PRIMARY_B}"].median(), width_atr=x[f"w_{sim.PRIMARY_B}"].median(),
        cost_R=BP * x[f"c_S_{P}"].mean(), M_same=x.M_same.mean()))
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).set_index("setup").T.round(4).to_string())
