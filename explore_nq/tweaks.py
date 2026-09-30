"""EXPLORATORY. Change one piece of the posted system at a time, on the development
period only, to see what each piece contributes. This is ~40 variants of a system
that already failed. Expect about two to reach |t| > 2 by chance; treat none of
this as a finding.

  python3 explore_nq/tweaks.py  -> explore_nq/tweaks_dev.csv
"""
import multiprocessing as mp
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_nq")
import mr

MARKETS = {"NQ": (0.25, 0.225), "ES": (0.25, 0.09), "RTY": (0.1, 0.09), "YM": (1.0, 0.9)}
VARIANTS = [("posted", {})]
VARIANTS += [(f"entry {k} ATR below", {"levels": ((k, 1.0),)}) for k in (0, 0.25, 0.5, 0.75, 1.5, 2.0)]
VARIANTS += [(f"target {t} ATR", {"target_atr": t}) for t in (0.5, 1.0, 1.5, 2.0)]
VARIANTS += [("no target", {"target_atr": np.inf})]
VARIANTS += [(f"stop {s} ATR", {"stop_atr": s}) for s in (0.75, 1.0, 2.5)] + [("no stop", {"stop_atr": np.inf})]
VARIANTS += [(f"time stop {m} min", {"time_stop": m}) for m in (5, 10, 30, 60)]
VARIANTS += [("no ER filter", {"er_max": np.inf}), ("ER <= 0.2", {"er_max": 0.2}),
             ("ER <= 0.5", {"er_max": 0.5}), ("ER > 0.35 (trending)", {"er_max": np.inf, "er_min": 0.35})]
VARIANTS += [(f"window {a[:5]}-{b[:5]}", {"window": (a, b)}) for a, b in
             (("09:30:00", "10:00:00"), ("12:00:00", "14:00:00"), ("14:00:00", "16:00:00"))]
VARIANTS += [("SHORT, mirrored", {"_mirror": True})]
VARIANTS += [(f"market {s}", {"_sym": s}) for s in ("ES", "RTY", "YM")]
VARIANTS += [("scale-in (B)", {"levels": ((1.0, 0.5), (1.5, 0.5))}),
             ("no commission", {"commission": 0.0}),
             ("no slippage, no commission", {"commission": 0.0, "tick": 1e-9})]
DATA = {}


def run(item):
    name, kw = item
    kw = dict(kw)
    sym = kw.pop("_sym", "NQ")
    m1 = DATA[sym]
    if kw.pop("_mirror", False):
        m1 = mr.mirror(m1)
    tick, com = MARKETS[sym]
    kw.setdefault("tick", tick)
    kw.setdefault("commission", com)
    tr = mr.simulate(m1, mr.bars3(m1), **kw)
    wk = tr.day.dt.to_period("W").astype(str)
    r = tr.pts_net / tr.atr
    m, se = mr.clustered(r, wk)
    gross = (tr.pts / tr.atr).mean()
    return dict(variant=name, trades=len(tr), win=(tr.pts_net > 0).mean(), gross_atr=gross,
                net_atr=m, se=se, t=m / se, net_pts=tr.pts_net.mean(),
                avg_target_atr=((tr.target - tr.entry) / tr.atr).mean())


if __name__ == "__main__":
    for s in MARKETS:
        DATA[s] = mr.load_nq("dev", s)
    with mp.get_context("fork").Pool(12) as pool:
        rows = pool.map(run, VARIANTS)
    out = pd.DataFrame(rows)
    out.to_csv("explore_nq/tweaks_dev.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
