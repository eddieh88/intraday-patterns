"""The sealed 2010-2014 run of prereg/own_fx_basket.md. Read once, with EARLY_UNLOCK=final-evaluation.

Spot (HistData bid/ask, net and gross) for the decision; CME futures 2008-2014 as a cross-check.

  EARLY_UNLOCK=final-evaluation python3 explore_fx/basket_holdout.py
"""
import glob
import itertools
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import data
import basket_match as B
from holdout import assert_early_sealed

TRIO = ("eurusd", "audusd", "nzdusd")
B.XS, B.WS, B.SS, B.CS = (0.4,), (6, 8, 10), (25, 30, 40, None), ("lon17", "ny11", "ny1655")


def spot_frames(start, end, gross=False):
    fr = {}
    for p in TRIO:
        d = data.load(p, "early")
        d = d[(d.index >= start - pd.Timedelta("10D")) & (d.index < end)]
        sp = d.spread_mean
        d = d.assign(ok=(sp <= 3 * sp.median()) & (sp <= sp.shift(1).rolling(4, min_periods=1).mean().fillna(np.inf) + 1e-9))
        if gross:
            for s in ("bid", "ask"):
                for c in ("open", "high", "low", "close"):
                    d[f"{s}_{c}"] = d[f"mid_{c}"]
        fr[p] = d
    idx = fr[TRIO[0]].index
    for p in TRIO[1:]:
        idx = idx.intersection(fr[p].index)
    return {p: fr[p].reindex(idx) for p in TRIO}, idx


def futures_frames(start, end):
    sym = {"eurusd": "E6", "audusd": "A6", "nzdusd": "N6"}
    rows = []
    for f in sorted(glob.glob("cache/mp_futures_5min_early/*.parquet")):
        day = pd.Timestamp(f.split("_")[-1][:10])
        if start - pd.Timedelta("10D") <= day < end:
            rows.append(pq.read_table(f, filters=[("symbol", "in", list(sym.values()))]).to_pandas())
    d = pd.concat(rows)
    d["ts"] = pd.to_datetime(d.timestamp)
    assert_early_sealed(d.ts)
    fr = {}
    for p, s in sym.items():
        g = d[d.symbol == s].drop_duplicates("ts").set_index("ts").sort_index()
        x = pd.DataFrame(index=g.index)
        for c in ("open", "high", "low", "close"):
            x[f"mid_{c}"] = x[f"bid_{c}"] = x[f"ask_{c}"] = g[c].values
        x["ok"] = True
        fr[p] = x
    idx = fr["eurusd"].index
    for p in TRIO[1:]:
        idx = idx.intersection(fr[p].index)
    idx = idx.astype("datetime64[ns]")                 # parquet gives microseconds; the engine expects ns
    return {p: fr[p].set_axis(fr[p].index.astype("datetime64[ns]")).reindex(idx) for p in TRIO}, idx


def portfolio(trades, start, end, cost_pips=0.0):
    t = trades[trades.ref == "prev_close"].copy()
    t["t_in"], t["t_out"] = pd.to_datetime(t.t_in), pd.to_datetime(t.t_out)
    if cost_pips:
        px = t.groupby("pair").bp.transform(lambda s: 1.0)              # placeholder, cost applied in pips below
        t["bp"] = t.bp - cost_pips * 1e-4 / (t.pips.abs() * 0 + 1) * 1e4 / t.pair.map({"eurusd": 1.3, "audusd": 0.9, "nzdusd": 0.75})
    days = pd.bdate_range(start, end - pd.Timedelta("1D"))
    curves, entries = [], []
    for _, g in t.groupby(["W", "close", "stop"]):
        per = g.groupby("t_in").agg(bp=("bp", "sum"), t_out=("t_out", "max"))
        per["bp"] /= 3
        curves.append(per.groupby(per.t_out.dt.normalize()).bp.sum().reindex(days, fill_value=0.0))
        entries.append(per.bp)
    daily = pd.concat(curves, axis=1).mean(axis=1)
    ent = pd.concat(entries, axis=1).mean(axis=1) if False else pd.concat(entries).groupby(level=0).mean() * len(entries) / 36
    return daily, ent


def report(label, daily, ent):
    yr = daily.groupby(daily.index.year).sum()
    eq = daily.cumsum()
    dd = (eq.cummax() - eq).max()
    yrs = len(daily) / 252
    mean = eq.iloc[-1] / yrs
    trim = ent.groupby(ent.index.year).apply(lambda s: s.sort_values().iloc[:-3].sum())
    print(f"\n{label}: mean {mean:+.0f} bp/yr, years positive {(yr > 0).sum()}/{len(yr)}, "
          f"return/maxDD {mean / dd if dd else 0:.2f}x/yr, max DD {dd:.0f} bp")
    print("  by year:", yr.round(0).to_dict())
    print("  minus top-3 entries per year:", trim.round(0).to_dict(), f"mean {trim.mean():+.0f}")
    return mean, int((yr > 0).sum()), (mean / dd if dd else 0)


if __name__ == "__main__":
    import sys
    s0, s1 = pd.Timestamp("2010-01-04"), pd.Timestamp("2015-01-01")
    res = {}
    only_futures = "--futures-only" in sys.argv
    for label, gross in ([] if only_futures else [("SPOT NET (decision)", False), ("SPOT GROSS (mid, no spread)", True)]):
        fr, idx = spot_frames(s0, s1, gross)
        B.FR.clear(); B.FR.update(fr); B.IDX = idx; B.START, B.END = s0, s1
        tr = B.run(TRIO)
        daily, ent = portfolio(tr, s0, s1)
        res[label] = report(label, daily, ent)
        for a, b in ((2010, 2012), (2013, 2014)):
            d = daily[(daily.index.year >= a) & (daily.index.year <= b)]
            print(f"  {a}-{b}: {d.sum() / (b - a + 1):+.0f} bp/yr")
    f0 = pd.Timestamp("2008-01-02")
    fr, idx = futures_frames(f0, s1)
    B.FR.clear(); B.FR.update(fr); B.IDX = idx; B.START, B.END = f0, s1
    tr = B.run(TRIO)
    daily, ent = portfolio(tr, f0, s1, cost_pips=1.0)
    report("FUTURES 2008-2014 (cross-check, 1 pip per leg)", daily, ent)
    if only_futures:
        raise SystemExit
    mean, up, rdd = res["SPOT NET (decision)"]
    verdict = "PASS" if (mean >= 100 and up >= 3 and rdd >= 0.4) else ("FAIL" if (mean <= 0 or up <= 1) else "INCONCLUSIVE")
    print(f"\nVERDICT (pre-registered, spot net): {verdict}")
