"""Sensitivity runs for prereg/nq_mean_reversion.md (reported without verdict), plus
one exploratory control added after the development run.

  - gross of commission, the optimistic fill minute, no efficiency-ratio filter
  - B against A: win rate and max drawdown of cumulative net points
  - EXPLORATORY (not registered): random long entries at the same minute of day on
    a random other day. The registered control samples the trade's own day. Days
    with many dips are down days, and they contribute the most draws, so that
    control leans toward falling mornings.

  python3 explore_nq/sensitivity.py [holdout]
"""
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_nq")
import mr


def max_dd(pts):
    eq = np.cumsum(pts)
    return float((np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]).max())


def other_day_control(m1, trades, n=20, seed=11):
    """Market buy at the trade's fill minute-of-day on n random other days, with the
    trade's target and stop distances and the same exits and costs."""
    rng = np.random.default_rng(seed)
    w = m1[(m1.index.time >= pd.Timestamp("10:00").time()) & (m1.index.time <= pd.Timestamp("12:00").time())]
    by_day = {d: g for d, g in w.groupby(w.index.normalize())}
    days = np.array(sorted(by_day))
    out = []
    for t in trades.itertuples():
        up, dn = t.target - t.entry, t.entry - t.stop
        tod = t.fill_t - t.day
        res = []
        for d in rng.choice(days[days != t.day], n):
            mm = by_day[d]
            ts, O, H, L, C = mm.index, mm.open.values, mm.high.values, mm.low.values, mm.close.values
            e = ts.searchsorted(d + tod)
            if e >= len(ts) - 1:
                continue
            t1 = d + pd.Timedelta(mr.WINDOW[1])
            entry = O[e] + mr.TICK
            tgt, stp = entry + up, entry - dn
            t_exit = min(ts[e] + pd.Timedelta("15min"), t1)
            px = None
            for j in range(e, len(ts)):
                if ts[j] >= t_exit:
                    px = O[j] - mr.TICK; break
                if L[j] <= stp:
                    px = stp - mr.TICK; break
                if H[j] >= tgt + mr.TICK and j > e:
                    px = tgt; break
            if px is None:
                px = C[-1] - mr.TICK
            res.append(px - entry - mr.COMMISSION)
        out.append(np.mean(res))
    return np.array(out)


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "dev"
    m1 = mr.load_nq(period)
    b3 = mr.bars3(m1)
    base = pd.read_parquet(f"cache/nq_mr_base_{period}.parquet")
    scale = pd.read_parquet(f"cache/nq_mr_scale_{period}.parquet")
    print(f"--- {period} ---")
    for tr, lab in ((base, "A"), (scale, "B")):
        print(f"{lab}: win {np.mean(tr.pts_net > 0):.1%}, max drawdown {max_dd(tr.pts_net):.0f} pts "
              f"(${max_dd(tr.pts_net) * 20:,.0f} per NQ), total {tr.pts_net.sum():+.0f} pts")
    mr.summary(mr.simulate(m1, b3, optimistic=True), "A, optimistic fill minute")
    mr.summary(mr.simulate(m1, b3, er_max=np.inf), "A, no ER filter")
    ctrl = other_day_control(m1, base)
    wk = base.day.dt.to_period("W").astype(str)
    m, se = mr.clustered(base.pts_net.values - ctrl, wk)
    print(f"{'A minus other-day random (EXPL.)':<34} control net={ctrl.mean():+6.2f}  "
          f"diff={m:+6.2f} ± {se:4.2f} pts (t {m / se:+5.2f})")
    print("A by year (net pts/trade):")
    print(base.groupby(base.day.dt.year).pts_net.agg(["count", "mean"]).round(2).to_string())
