"""Walk-forward of the evening dollar-basket fade (basket_match.py) on development spot FX,
2015-01 .. 2026-09, at HistData bid/ask. The 2010-2014 holdout stays sealed.

Each test year Y (2018..2026) uses only the three years before it to choose settings
(trio, reference, window W, threshold X, close, stop), then trades Y unchanged. Selection by
return per max drawdown on the training years, requiring >= 30 groups. Three selection modes:
  best   : the single best setting
  top10  : the equal-weight average of the 10 best settings
  region : fixed EUR+AUD+NZD / prev_close / X 0.4 (the region found in development), the
           median over its W, close and stop variants (no selection; the honest number)
P&L: bp per leg, summed per group and divided by 3 (one unit of capital per group).
Overnight swap: trades are counted for crossings of the 17:00 New York rollover (where swap
is charged); the rule enters after 17:00 and exits before the next 17:00, so it should be ~0.

  python3 explore_fx/basket_wf.py -> explore_fx/basket_wf.csv (yearly out-of-window results)
"""
import itertools
import multiprocessing as mp
import os
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import basket_match as B

B.START, B.END = pd.Timestamp("2015-01-05"), pd.Timestamp("2026-09-25")
CACHE = "cache/basket_wf_trades.parquet"
KEYS = ["trio", "ref", "W", "X", "close", "stop"]


def rollover_crossings(t_in, t_out):
    """Number of 17:00 New York instants inside (t_in, t_out]."""
    first = t_in.dt.normalize() + pd.Timedelta("17:00:00")
    first = first.where(first > t_in, first + pd.Timedelta("1D"))
    return ((t_out - first).dt.total_seconds() // 86400 + 1).clip(lower=0) * (t_out >= first)


def stats(daily):
    eq = daily.cumsum()
    dd = (eq.cummax() - eq).max()
    yrs = len(daily) / 252
    ann = eq.iloc[-1] / yrs if yrs else 0
    vol = daily.std() * np.sqrt(252)
    return ann, (ann / vol if vol else 0), (ann / dd if dd else 0)


def daily_pnl(g, days):
    per_group = g.groupby("t_in").bp.sum() / 3
    d = per_group.groupby(pd.to_datetime(g.groupby("t_in").t_out.max()).dt.normalize().values).sum()
    return d.reindex(days, fill_value=0.0)


if __name__ == "__main__":
    if os.path.exists(CACHE) and "--resim" not in sys.argv:
        trades = pd.read_parquet(CACHE)
    else:
        fr, idx = B.load_all()
        B.FR.update(fr)
        B.IDX = idx
        trios = list(itertools.combinations(B.PAIRS, 3))
        with mp.get_context("fork").Pool(10) as pool:
            parts = pool.map(B.run, trios)
        for tr, df in zip(trios, parts):
            df["trio"] = "+".join(tr)
        trades = pd.concat(parts, ignore_index=True)
        trades.to_parquet(CACHE)
    trades["t_in"] = pd.to_datetime(trades.t_in)
    trades["t_out"] = pd.to_datetime(trades.t_out)
    cross = rollover_crossings(trades.t_in, trades.t_out)
    print(f"{len(trades):,} legs; share crossing the 17:00 rollover: {np.mean(cross > 0):.2%}")
    days = pd.bdate_range("2015-01-05", "2026-09-25")
    groups = {k: g for k, g in trades.groupby(KEYS)}
    rows = []
    for Y in range(2018, 2027):
        tr0, tr1 = pd.Timestamp(f"{Y - 3}-01-01"), pd.Timestamp(f"{Y}-01-01")
        te1 = pd.Timestamp(f"{Y + 1}-01-01")
        tdays = days[(days >= tr0) & (days < tr1)]
        ydays = days[(days >= tr1) & (days < te1)]
        scores = []
        for k, g in groups.items():
            gt = g[(g.t_in >= tr0) & (g.t_in < tr1)]
            if gt.t_in.nunique() < 30:
                continue
            scores.append((stats(daily_pnl(gt, tdays))[2], k))
        scores.sort(reverse=True)
        best_k = scores[0][1]
        top = [k for _, k in scores[:10]]
        test = {k: daily_pnl(groups[k][(groups[k].t_in >= tr1) & (groups[k].t_in < te1)], ydays) for k in set(top)}
        region_keys = [k for k in groups if k[0] == "eurusd+audusd+nzdusd" and k[1] == "prev_close" and k[3] == 0.4]
        region = [daily_pnl(groups[k][(groups[k].t_in >= tr1) & (groups[k].t_in < te1)], ydays) for k in region_keys]
        for mode, d in (("best", test[best_k]), ("top10", pd.concat([test[k] for k in top], axis=1).mean(axis=1)),
                        ("region", pd.concat(region, axis=1).median(axis=1))):
            rows.append(dict(year=Y, mode=mode, ret_bp=float(d.sum()), chosen="|".join(map(str, best_k)) if mode == "best" else ""))
    res = pd.DataFrame(rows)
    res.to_csv("explore_fx/basket_wf.csv", index=False, float_format="%.2f")
    pd.set_option("display.width", 200)
    print("\nOut-of-window return by year (bp of capital, 1x notional per leg):")
    print(res.pivot(index="year", columns="mode", values="ret_bp").round(0).to_string())
    print("\nchosen 'best' settings by year:")
    print(res[res["mode"] == "best"][["year", "chosen"]].to_string(index=False))
    for mode in ("best", "top10", "region"):
        s = res[res["mode"] == mode].ret_bp
        print(f"{mode}: mean {s.mean():+.0f} bp/yr, years positive {(s > 0).sum()}/{len(s)}")
