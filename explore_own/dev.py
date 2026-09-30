"""Development grid for our own FX strategies on 2021-2026 spot bid/ask
(explore_own/strategies.py). Development only; the 2010-2020 period stays sealed.

  night : Bollinger(n, k) on 5-minute mids, entries 20:00-01:00 New York, flat 02:00,
          exit "mid" (target the band middle, 2x stop) or "bracket" (1:1)
          n in {20, 50}, k in {2.0, 2.5, 3.0}                      -> 12 variants
  gap   : weekend-gap fade, x in {0.1, 0.2, 0.3}%, stop s in {0.3, 0.5}%,
          rr in {1, 2}, wait in {5, 60} minutes after the reopen   -> 24 variants
Each variant runs on 8 pairs. Spread filter: cap = 3x the pair's overnight median,
plus the 240-second rule.

  python3 explore_own/dev.py -> explore_own/dev_night.csv, dev_gap.csv
"""
import itertools, multiprocessing as mp
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_nq")
import data, strategies as st, mr

PAIRS = ["eurgbp", "eurchf", "audnzd", "eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]
CAP = {"eurgbp": 2.7, "eurchf": 3.3, "audnzd": 6.2, "eurusd": 1.0, "gbpusd": 2.8,
       "audusd": 3.0, "nzdusd": 3.3, "usdjpy": 1.7}                  # 3x overnight median, pips
NIGHT = [dict(n=n, k=k, exit=e) for n, k, e in itertools.product((20, 50), (2.0, 2.5, 3.0), ("mid", "bracket"))]
GAP = [dict(x=x, s=s, rr=rr, wait=w) for x, s, rr, w in itertools.product((0.1, 0.2, 0.3), (0.3, 0.5), (1, 2), (5, 60))]
D = {}


def job(a):
    fam, pair, kw = a
    f = st.night if fam == "night" else st.gap
    t = f(D[pair], cap=CAP[pair], **kw)
    return fam, pair, tuple(sorted(kw.items())), t


def stats(t):
    if len(t) < 10:
        return dict(trades=len(t))
    m, se = mr.clustered(t.bp, t.t_in.dt.to_period("W").astype(str))
    yrs = t.groupby(t.t_in.dt.year).bp.sum()
    return dict(trades=len(t), win=(t.bp > 0).mean(), bp=m, t=m / se, spread_bp=t.spread_bp.mean(),
                years_up=f"{(yrs > 0).sum()}/{len(yrs)}")


if __name__ == "__main__":
    for p in PAIRS:
        D[p] = data.load(p)
    jobs = [("night", p, kw) for p in PAIRS for kw in NIGHT] + [("gap", p, kw) for p in PAIRS for kw in GAP]
    with mp.get_context("fork").Pool(12) as pool:
        res = pool.map(job, jobs)
    pd.set_option("display.width", 220)
    for fam in ("night", "gap"):
        rows = []
        by_kw = {}
        for f, p, kw, t in res:
            if f != fam:
                continue
            rows.append(dict(pair=p, **dict(kw), **stats(t)))
            by_kw.setdefault(kw, []).append(t.assign(pair=p))
        per_pair = pd.DataFrame(rows)
        pooled = pd.DataFrame([dict(**dict(kw), **stats(pd.concat(ts))) for kw, ts in by_kw.items()])
        per_pair.to_csv(f"explore_own/dev_{fam}.csv", index=False, float_format="%.3f")
        print(f"\n=== {fam}: pooled over 8 pairs ===")
        print(pooled.sort_values("t", ascending=False).round(2).to_string(index=False))
        print(f"--- {fam}: best 12 pair-variants ---")
        print(per_pair.sort_values("t", ascending=False).head(12).round(2).to_string(index=False))
