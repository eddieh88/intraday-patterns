"""Compact OHLCV subset for the Colab chart-pattern experiment.

Run, then upload /tmp/colab_ohlcv.parquet to the notebook.

VALIDATION FINDINGS (MarketParquet daily, 2010-2026, top-500-as-of-2010):
  THMO  close range [0.0000, 23,040,000] -- reverse-split adjustment applied
        but 4-decimal storage rounds modern sub-penny prices to zero.  Its
        corrupt $23M adjusted price also inflated its dollar volume enough to
        select it INTO the universe.  Bad data selecting itself in.
  DRYS, DFFN, OSAT, ZNB  same serial-reverse-split range blowup.
  GAP   136 jumps >300% in seven months of 2010 -- two price scales
        interleaved by date.
  SAF   close to 69,100, 31 jumps -- reverse split plus ticker reuse.
  COMS  0.93 -> 0.0014.
  SHEL  2012-05-23 close 63.20 above high 62.78 (7 such rows panel-wide).
  CHK, FST, NIHD, PCX, Q, SHLD, UPL, WOLF  one unadjusted reverse split each;
        flagged as bad_day rather than dropped.

Schema drift: most files name the date column "timestamp", some "date"; the
mixed date32/timestamp types concat to an object column that breaks sorting.


Universe is chosen by dollar volume as of 2010 and then FROZEN -- names that
later delisted stay in.  Selecting by recent liquidity would bake in exactly
the survivorship bias this project spent the day removing.  The -DELISTED
suffix is stripped: the tag encodes the future.
"""
import pandas as pd, numpy as np, glob, re
files = sorted(glob.glob("cache/mp/stock_daily_*.parquet"))
files = [f for f in files if "2010-01" <= re.search(r"(\d{4}-\d{2})", f).group(1)]
print(f"{len(files)} daily files from 2010-01", flush=True)

# universe: top 500 by dollar volume over the first 60 trading days of 2010
def rd(f):
    d = pd.read_parquet(f)
    if "date" in d.columns: d = d.rename(columns={"date": "timestamp"})
    d["timestamp"] = pd.to_datetime(d.timestamp)
    return d[["timestamp","symbol","open","high","low","close","volume"]]

head = pd.concat([rd(f) for f in files[:60]])
head["symbol"] = head.symbol.str.replace("-DELISTED", "", regex=False)
dv = (head.close * head.volume).groupby(head.symbol).mean()
univ = set(dv.nlargest(500).index)
print(f"universe frozen at 500 names as of 2010", flush=True)

out = []
for i, f in enumerate(files):
    d = rd(f)
    d["symbol"] = d.symbol.str.replace("-DELISTED", "", regex=False)
    out.append(d[d.symbol.isin(univ)])
    if i % 800 == 0: print(f"  {i}/{len(files)}", flush=True)
df = pd.concat(out, ignore_index=True)
df["timestamp"] = pd.to_datetime(df.timestamp)   # date32 + timestamp -> object
for c in ("open","high","low","close"): df[c] = df[c].astype("float32")
df["volume"] = df.volume.astype("float32")
df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
df.to_parquet("/tmp/colab_ohlcv.parquet", compression="zstd", index=False)
import os
alive = df.groupby("symbol").timestamp.max()
print(f"\nrows {len(df):,}  names {df.symbol.nunique()}  "
      f"{df.timestamp.min().date()}..{df.timestamp.max().date()}")
print(f"names whose series ends early (delisted): "
      f"{(alive < df.timestamp.max() - pd.Timedelta(days=30)).sum()}")
print(f"file: {os.path.getsize('/tmp/colab_ohlcv.parquet')/1e6:.0f} MB")
