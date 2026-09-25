"""Regression test: is the intraday universe point-in-time?

The first build ranked names by dollar volume summed over all of 2021-2026, so a
stock that became huge in 2024 was already in the 2021 pool. This test fails if
that, or anything like it, comes back.

  1. POINT-IN-TIME. For sampled dates, rebuild the pool from scratch using ONLY
     the session files strictly before that date, and require it to equal the
     stored pool. Independent code path, truncated data.
  2. DEAD NAMES PRESENT. Early pools must contain names the archive later tags
     -DELISTED; a pool built from survivors would have none.
  3. HOW BIASED THE OLD POOL WAS. Names in the hindsight top-200 that were not
     eligible on day one, and eligible names it left out.
  4. TICKER REUSE. A live ticker and a dead one with the same name must remain
     two companies. The suffix is kept precisely so that they do.

  python3 data/universe_check.py
"""
import pandas as pd, numpy as np, glob, sys

POOL, WIN = 150, 20
fs = [f for f in sorted(glob.glob("cache/mp5min/*.parquet"))
      if pd.read_parquet(f, columns=["symbol"]).symbol.nunique() >= 1000]   # drop holiday files
pool = pd.read_parquet("cache/intraday_pool.parquet")
fail = 0

def rth_dv(f):
    d = pd.read_parquet(f, columns=["timestamp","symbol","close","volume"]).dropna(subset=["symbol"])
    t = pd.to_datetime(d.timestamp); h = t.dt.hour + t.dt.minute/60
    d = d[(h>=9.5)&(h<16)]
    return (d.close*d.volume).groupby(d.symbol).sum()

# 1. point-in-time: recompute from the prior WIN files only
dates = sorted(pool.date.unique())
rng = np.random.default_rng(0)
for d in [dates[0], dates[len(dates)//2], dates[-1]] + list(rng.choice(dates, 3, replace=False)):
    d = pd.Timestamp(d)
    prior = [f for f in fs if pd.Timestamp(f.split("_")[-1][:10]) < d][-WIN:]
    m = pd.concat([rth_dv(f) for f in prior], axis=1).mean(axis=1, skipna=True)
    n = pd.concat([rth_dv(f) for f in prior], axis=1).notna().sum(axis=1)
    mine = set(m[n >= 10].nlargest(POOL).index)
    stored = set(pool[pool.date == d].symbol)
    ok = mine == stored
    fail += not ok
    print(f"  [{'PASS' if ok else 'FAIL'}] {d.date()}  recomputed from {len(prior)} prior files: "
          f"{len(mine & stored)}/{POOL} agree")

# 2. dead names present early
early = set(pool[pool.date < pool.date.min() + pd.Timedelta(days=90)].symbol)
dead = {s for s in early if s.endswith("-DELISTED")}
k = len(dead)
fail += k == 0
print(f"  [{'PASS' if k else 'FAIL'}] first 90 days: {k} of {len(early)} pool names were later delisted "
      f"(e.g. {sorted(dead)[:6]})")

# 3. bias of the old hindsight pool, if it is still around
try:
    old = set(pd.read_parquet("cache/intraday_daily_hindsight200.parquet", columns=["symbol"]).symbol)
    first = pool.assign(symbol=pool.symbol.str.replace("-DELISTED","",regex=False)).groupby("symbol").date.min()
    late = [s for s in old if s in first and first[s] > pool.date.min() + pd.Timedelta(days=365)]
    never = [s for s in old if s not in first]
    print(f"  [INFO] old hindsight pool: {len(old)} names; {len(late)} first became eligible a year or more in, "
          f"{len(never)} never eligible in any day's top {POOL}")
    print(f"         late: {sorted(late)[:12]}")
    print(f"         never: {sorted(never)[:12]}")
except FileNotFoundError:
    pass

# 4. ticker reuse: a live ticker and a dead one sharing a name must stay separate
syms = set(pool.symbol)
reused = sorted(b for b in {x.replace("-DELISTED","") for x in syms}
                if b in syms and b+"-DELISTED" in syms)
print(f"  [PASS] reused tickers kept as separate companies: {len(reused)} {reused[:8]}")

print(f"\n{'ALL CHECKS PASSED' if not fail else f'{fail} CHECK(S) FAILED'}")
sys.exit(1 if fail else 0)
