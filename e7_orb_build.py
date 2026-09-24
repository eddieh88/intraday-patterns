"""E7 pass 1: build the daily table needed to pick 'Stocks in Play'.

Per symbol-day: the 09:30-09:35 opening-range bar, the day's RTH OHLC, and
trailing dollar volume.  Relative volume and the top-20 selection are computed
afterwards from this table, so the selection can be audited separately from
the trade simulation.
"""
import pandas as pd, numpy as np, glob, time

fs = sorted(glob.glob("cache/mp5min/*.parquet"))
print(f"{len(fs)} sessions", flush=True)
out, t0 = [], time.time()
for i, f in enumerate(fs):
    d = pd.read_parquet(f, columns=["timestamp","symbol","open","high","low","close","volume"])
    d["symbol"] = d.symbol.str.replace("-DELISTED", "", regex=False)
    t = pd.to_datetime(d.timestamp); h = t.dt.hour + t.dt.minute/60
    d = d.assign(h=h).sort_values("timestamp")
    rth = d[(d.h >= 9.5) & (d.h < 16)]
    if not len(rth): continue
    orb = rth[rth.h < 9.5 + 5/60]                     # the 09:30-09:35 bar
    g = rth.groupby("symbol")
    a = pd.DataFrame({
        "hi_rth": g.high.max(), "lo_rth": g.low.min(),
        "o_rth":  g.open.first(), "c_rth": g.close.last(),
        "dv":     (rth.close*rth.volume).groupby(rth.symbol).sum(),
    })
    b = orb.groupby("symbol").agg(or_o=("open","first"), or_h=("high","max"),
                                  or_l=("low","min"), or_c=("close","last"),
                                  or_v=("volume","sum"))
    a = a.join(b, how="inner")
    a["date"] = t.iloc[0].normalize()
    out.append(a.reset_index())
    if i % 200 == 0: print(f"  {i}/{len(fs)}  {time.time()-t0:.0f}s", flush=True)

D = pd.concat(out, ignore_index=True).sort_values(["symbol","date"])
# trailing quantities -- all shifted, so known before the day starts
g = D.groupby("symbol")
D["dv20"]    = g.dv.transform(lambda x: x.shift(1).rolling(20, min_periods=10).mean())
D["orv14"]   = g.or_v.transform(lambda x: x.shift(1).rolling(14, min_periods=7).mean())
tr = pd.concat([D.hi_rth-D.lo_rth,
                (D.hi_rth-g.c_rth.shift(1)).abs(),
                (D.lo_rth-g.c_rth.shift(1)).abs()], axis=1).max(axis=1)
D["atr14"]   = tr.groupby(D.symbol).transform(lambda x: x.shift(1).rolling(14, min_periods=7).mean())
D["relvol"]  = D.or_v / D.orv14
D.to_parquet("cache/orb_daily.parquet", index=False)
print(f"\n{len(D):,} symbol-days, {D.date.nunique()} sessions, {D.symbol.nunique():,} names")
print(f"-> cache/orb_daily.parquet  ({time.time()-t0:.0f}s)")
