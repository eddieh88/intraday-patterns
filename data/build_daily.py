"""Build ONE daily summary table from the 5-minute archive, then cache it.

Every intraday experiment needs the same per-symbol-per-day fields: the
overnight move, the opening range, the rest of the session.  Recomputing them
per experiment meant a 30-minute groupby.apply each time.  Aggregate once with
vectorised named-aggregations, cache, and every test afterwards is seconds.

  python3 data/build_daily.py      -> cache/intraday_daily.parquet
                                  -> cache/intraday_pool.parquet (who was eligible, each day)
"""
import pandas as pd, numpy as np, glob, time

POOL, WIN = 150, 20       # names kept per day; trailing sessions for the volume rank
fs = sorted(glob.glob("cache/mp5min/*.parquet"))
print(f"{len(fs)} session files")

# pass 1: RTH dollar volume for EVERY symbol on EVERY day, then a point-in-time pool.
#
# The first version summed dollar volume over all of 2021-2026 and kept the top
# 200 -- so a stock that became huge in 2024 was in the 2021 pool because of
# what happened in 2024. The pool itself used future volume. Now each day's pool
# is ranked on the mean of the PRIOR WIN sessions only (shift(1)), and every
# name that is ever in any day's top POOL is kept. Experiments then take their
# own top-100 per day from this table; POOL > 100 is the buffer that guarantees
# every such name is present.
#
# The vendor also writes a file for each US market holiday holding a handful of
# symbols. Those are not sessions: they are dropped here and in pass 2.
rows, holidays, t0 = {}, [], time.time()
for i, f in enumerate(fs):
    d = pd.read_parquet(f, columns=["timestamp","symbol","close","volume"]).dropna(subset=["symbol"])
    if d.symbol.nunique() < 1000: holidays.append(f); continue
    t = pd.to_datetime(d.timestamp); h = t.dt.hour + t.dt.minute/60
    d = d[(h>=9.5)&(h<16)]
    rows[t.iloc[0].normalize()] = (d.close*d.volume).groupby(d.symbol).sum()
    if i%200==0: print(f"  pass 1: {i}/{len(fs)}  {time.time()-t0:.0f}s", flush=True)
print(f"dropped {len(holidays)} holiday files: {[f.split('_')[-1][:10] for f in holidays]}")
fs = [f for f in fs if f not in holidays]
# dates x symbols. Mean over the prior WIN market sessions, at least 10 present.
W = pd.DataFrame(rows).T.sort_index()
prior = W.rolling(WIN, min_periods=10).mean().shift(1)
rk = prior.rank(axis=1, ascending=False, method="first")
pool = rk.stack().rename("rk").reset_index().rename(columns={"level_0":"date","level_1":"symbol"})
pool = pool[pool.rk <= POOL]
pool.to_parquet("cache/intraday_pool.parquet", index=False)
univ = set(pool.symbol)
print(f"universe: {len(univ)} names ever in a day's point-in-time top {POOL}  ({time.time()-t0:.0f}s)")

# pass 2: one row per symbol-day
def block(h):
    return np.select([h<9.5, h<10.0, h<11.0, h<16.0], ["pre","or","open","rth"], "post")

out, t0 = [], time.time()
for i,f in enumerate(fs):
    d = pd.read_parquet(f, columns=["timestamp","symbol","open","high","low","close","volume"])
    # The -DELISTED suffix is KEPT as part of the symbol. It is applied to a dead
    # company's entire history, so it identifies that company uniquely. Stripping it
    # merged two companies into one series whenever a ticker was reused (BBBY, FISV).
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
