"""Timestamp audit for prereg/selection.md. Every check must pass before step 3.

  1. BAR CONVENTION. Bars are stamped at their start: regular hours are exactly
     the 78 stamps 09:30..15:55, or 09:30..12:55 on a detected early close.
     Every "before 09:45" rule depends on this. A known half day is always tested.
  2. STAGE A. Scramble every bar stamped 09:45 or later. The AT0945 columns must
     not change; the EOD columns must (proving the scramble reached them).
  3. STAGE B. For sampled dates d, replace that day's EOD fields and EVERY field
     of every later day with noise. Features on d must not change.
  4. THE AUDIT CAN FAIL. Remove one .shift(1) from the feature code and rerun
     check 3; it must now report a leak.
  5. HOLDOUT. Nothing on or after 2025-04-01 anywhere.

  python3 selection/test_audit.py
"""
import pandas as pd, numpy as np, glob, sys, inspect, types
from paths import add_to_path
add_to_path("selection")
from holdout import HOLDOUT_START
import session_summary as A, features as B

rng = np.random.default_rng(7)
fail = 0
def report(ok, msg):
    global fail; fail += not ok; print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")

files = [f for f in sorted(glob.glob("cache/mp5min/*.parquet"))
         if pd.Timestamp(f.split("_")[-1][:10]) < HOLDOUT_START]
sample = [files[i] for i in rng.choice(len(files), 3, replace=False)]

# 1. bar convention
half = [f for f in files if f.split("_")[-1][:10] == "2023-11-24"]      # a known early close
for f in sample + half:
    full = pd.read_parquet(f, columns=["timestamp","symbol","volume"]).dropna(subset=["symbol"])
    close_h = A.session_close(full); last = "12:55" if close_h < 16 else "15:55"
    d = full[full.symbol == "AAPL"]
    hm = pd.to_datetime(d.timestamp).dt.strftime("%H:%M")
    rth = sorted(set(hm[(hm >= "09:30") & (hm <= last)]))
    grid = [f"{h:02d}:{m:02d}" for h in range(9, 16) for m in range(0, 60, 5) if "09:30" <= f"{h:02d}:{m:02d}" <= last]
    report(rth == grid, f"{f.split('_')[-1][:10]}: AAPL regular-hours stamps are exactly 09:30..{last} "
                        f"({len(rth)} bars{', early close' if close_h < 16 else ''})")

# 2. stage A
for f in sample:
    d = pd.read_parquet(f, columns=A.COLS).dropna(subset=["symbol"])
    d = d[d.symbol.isin(d.symbol.drop_duplicates().sample(60, random_state=1))]
    t = pd.to_datetime(d.timestamp); late = (t.dt.hour + t.dt.minute/60 >= 9.75).values
    z = d.copy()
    for col in ["open","high","low","close","volume"]:
        z.loc[late, col] = z.loc[late, col] * rng.uniform(0.3, 3.0, late.sum())
    z = z.sample(frac=1, random_state=2)                         # order must not matter either
    a, b = A.summarise(d), A.summarise(z)
    same = all(np.allclose(a[c], b.loc[a.index, c], equal_nan=True) for c in A.AT0945)
    moved = any(not np.allclose(a[c], b.loc[a.index, c], equal_nan=True) for c in A.EOD)
    report(same and moved, f"{f.split('_')[-1][:10]}: AT0945 fields unchanged by scrambling 09:45+ bars; EOD fields changed")

# 3 and 4. stage B
S = pd.read_parquet("cache/sel_stocks.parquet"); E = pd.read_parquet("cache/sel_etfs.parquet")
pool = pd.read_parquet("cache/intraday_pool.parquet"); pool = pool[pool.rk <= 100]
fomc = pd.read_csv("data/calendar/fomc_decisions.csv", parse_dates=["date"]).date
dates = sorted(S.date.unique())
test_days = [dates[i] for i in rng.choice(np.arange(140, len(dates) - 35), 6, replace=False)]
NUM_S = A.AT0945 + A.EOD

def corrupt(df, d, cols):
    z = df.copy()
    fut, today = z.date > d, z.date == d
    z.loc[fut, cols] = z.loc[fut, cols].values * rng.uniform(0.3, 3.0, (fut.sum(), len(cols)))
    z.loc[today, A.EOD] = z.loc[today, A.EOD].values * rng.uniform(0.3, 3.0, (today.sum(), len(A.EOD)))
    return z

def leaks(build):
    bad = []
    for d in test_days:
        i = dates.index(d); lo, hi = dates[i - 135], dates[i + 30]
        win = lambda df: df[(df.date >= lo) & (df.date <= hi)]
        clean = build(win(S), win(E), pool, fomc)
        dirty = build(corrupt(win(S), d, NUM_S), corrupt(win(E), d, NUM_S), pool, fomc)
        a = clean[clean.date == d].set_index("symbol"); b = dirty[dirty.date == d].set_index("symbol")
        cols = [c for c in a.columns if c != "date"]
        diff = [c for c in cols if not np.allclose(a[c].astype(float), b.loc[a.index, c].astype(float), equal_nan=True)]
        if diff or len(a) != len(b): bad.append((pd.Timestamp(d).date(), diff))
    return bad

bad = leaks(B.build)
report(not bad, f"stage B: features on {len(test_days)} dates unchanged when that day's EOD and all later data are noise"
                + (f" -- LEAKS: {bad}" if bad else ""))

src = inspect.getsource(B).replace("rng.rolling(14, min_periods=10).mean().shift(1)",
                                   "rng.rolling(14, min_periods=10).mean()")          # plant a leak
mutant = types.ModuleType("mutant"); exec(compile(src, "mutant", "exec"), mutant.__dict__)
caught = leaks(mutant.build)
report(bool(caught) and all("gap" in d or "or15_range" in d for _, d in caught),
       f"mutation test: removing one .shift(1) is caught on {len(caught)}/{len(test_days)} dates "
       f"({sorted(set(c for _, d in caught for c in d))})")

# 5. holdout
T = pd.read_parquet("cache/sel_features.parquet")
report(max(S.date.max(), E.date.max(), T.date.max()) < HOLDOUT_START,
       f"holdout sealed: last date in any stage is {max(S.date.max(), T.date.max()).date()}")

print(f"\n{'ALL CHECKS PASSED' if not fail else f'{fail} CHECK(S) FAILED'}")
sys.exit(1 if fail else 0)
