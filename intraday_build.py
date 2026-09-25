"""Build ONE daily summary table from the 5-minute archive, then cache it.

Every intraday experiment needs the same per-symbol-per-day fields: the
overnight move, the opening range, the rest of the session.  Recomputing them
per experiment meant a 30-minute groupby.apply each time.  Aggregate once with
vectorised named-aggregations, cache, and every test afterwards is seconds.

  python3 intraday_build.py      -> cache/intraday_daily.parquet
"""
import pandas as pd, numpy as np, glob, time

TOPN = 200
fs = sorted(glob.glob("cache/mp5min/*.parquet"))
print(f"{len(fs)} session files")

# pass 1: pick the universe by RTH dollar volume, cheaply
dv = {}
for f in fs[::10]:
    d = pd.read_parquet(f, columns=["timestamp","symbol","close","volume"])
    t = pd.to_datetime(d.timestamp); h = t.dt.hour + t.dt.minute/60
    d = d[(h>=9.5)&(h<16)]
    s = (d.close*d.volume).groupby(d.symbol.str.replace("-DELISTED","",regex=False)).sum()
    for k,v in s.items(): dv[k] = dv.get(k,0)+v
univ = set(pd.Series(dv).nlargest(TOPN).index)
print(f"universe: top {TOPN} by RTH dollar volume")

# pass 2: one row per symbol-day
def block(h):
    return np.select([h<9.5, h<10.0, h<11.0, h<16.0], ["pre","or","open","rth"], "post")

out, t0 = [], time.time()
for i,f in enumerate(fs):
    d = pd.read_parquet(f, columns=["timestamp","symbol","open","high","low","close","volume"])
    d["symbol"] = d.symbol.str.replace("-DELISTED","",regex=False)
    d = d[d.symbol.isin(univ)]
    if not len(d): continue
    t = pd.to_datetime(d.timestamp); h = t.dt.hour + t.dt.minute/60
    d = d.assign(h=h, blk=block(h.values)).sort_values("timestamp")
    g = d.groupby(["symbol","blk"])
    a = g.agg(o=("open","first"), c=("close","last"), hi=("high","max"),
              lo=("low","min"), v=("volume","sum"), n=("close","size"))
    w = a.unstack("blk")
    w.columns = [f"{x}_{y}" for x,y in w.columns]
    w["date"] = t.iloc[0].normalize()
    out.append(w.reset_index())
    if i%50==0: print(f"  {i}/{len(fs)}  {time.time()-t0:.0f}s", flush=True)

D = pd.concat(out, ignore_index=True).sort_values(["symbol","date"])
# prior-day RTH levels
for col,new in (("hi_rth","pdh"),("lo_rth","pdl"),("c_rth","pdc")):
    D[new] = D.groupby("symbol")[col].shift(1)
D.to_parquet("cache/intraday_daily.parquet", index=False)
print(f"\n{len(D):,} symbol-days, {D.date.nunique()} sessions, {D.symbol.nunique()} names")
print(f"columns: {[c for c in D.columns]}")
print(f"-> cache/intraday_daily.parquet  ({time.time()-t0:.0f}s)")
