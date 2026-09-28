"""Time-of-day volume baseline: for each name and 5-minute slot, the mean volume in
that slot over the PRIOR 20 sessions (the day itself excluded). Development only.

  python3 explore5m/slot_volume.py   -> cache/x5_slotvol.parquet
"""
import pandas as pd, numpy as np, glob, sys, time
from holdout import HOLDOUT_START
t0 = time.time()
pool = pd.read_parquet("cache/intraday_pool.parquet"); pool = pool[(pool.rk <= 100) & (pool.date < HOLDOUT_START)]
names = set(pool.symbol)
rows = []
for f in sorted(glob.glob("cache/mp5min/*.parquet")):
    day = pd.Timestamp(f.split("_")[-1][:10])
    if day >= HOLDOUT_START: break
    d = pd.read_parquet(f, columns=["timestamp","symbol","volume"]).dropna(subset=["symbol"])
    if d.symbol.nunique() < 1000: continue
    d = d[d.symbol.isin(names)]
    t = pd.to_datetime(d.timestamp); d = d.assign(date=day, slot=(t.dt.hour * 60 + t.dt.minute).astype("int16"))
    rows.append(d[(d.slot >= 570) & (d.slot < 960)][["date","symbol","slot","volume"]])
S = pd.concat(rows, ignore_index=True); S["symbol"] = S.symbol.astype("category")
W = S.pivot_table(index="date", columns=["symbol","slot"], values="volume", observed=True).sort_index()
norm = W.rolling(20, min_periods=10).mean().shift(1)            # prior 20 sessions only
N = norm.stack(["symbol","slot"], future_stack=True).rename("slot_norm").reset_index().dropna()
N.to_parquet("cache/x5_slotvol.parquet", index=False)
print(f"{len(N):,} (date, name, slot) baselines  ({time.time()-t0:.0f}s)")
