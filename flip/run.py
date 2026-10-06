"""Run the silent flip on real 5-minute bars, one calendar month per worker.

  python3 flip/run.py              -> cache/flip_dev.parquet       (development only)
  HOLDOUT_UNLOCK=final-evaluation python3 flip/run.py holdout
                                   -> cache/flip_holdout.parquet   (once, see the prereg)

Each month warms up on the sessions before it, so the flip levels can look back 20
sessions and the fake levels can draw from them.
"""
import glob, sys, time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("flip", "selection")
import sim
from session_summary import session_close
from holdout import HOLDOUT_START, assert_sealed

COLS = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
DAY = lambda f: pd.Timestamp(f.split("_")[-1][:10])
WARM = sim.LOOKBACK + 3


def sessions(f, names):
    """symbol -> RTH (o, h, l, c, hh) arrays for one file."""
    full = pd.read_parquet(f, columns=COLS).dropna(subset=["symbol"])
    close_h = session_close(full)
    d = full[full.symbol.isin(names)]
    t = pd.to_datetime(d.timestamp)
    d = d.assign(h=(t.dt.hour + t.dt.minute / 60).values, ts=t.values).sort_values("ts")
    d = d[(d.h >= 9.5) & (d.h < close_h)]
    return {s: tuple(g[k].values.astype(float) for k in ("open", "high", "low", "close", "h"))
            for s, g in d.groupby("symbol")}


def run_month(job):
    month, files, warm, by_day, allnames = job
    hist, rows = {}, []
    rng = np.random.default_rng([sim.SEED, month.year, month.month])
    for f in warm + files:
        day, live = DAY(f), f in files
        names = by_day.get(day, set())
        for s, (o, h, l, c, hh) in sessions(f, allnames).items():
            if len(c) < 6:
                continue
            H = hist.setdefault(s, [])
            if live and s in names:
                r, today = sim.name_day(o, h, l, c, hh, H, rng)
                for x in r:
                    x["date"], x["symbol"] = day, s
                rows += r
            else:
                _, today = sim.name_day(o, h, l, c, hh, [], rng)     # record only
                if len(H) >= 2:
                    today["ratios"] = np.array(sim.levels_from(H)) / o[0]
            H.append(today)
            del H[:-(sim.LOOKBACK + 2)]
    return rows


def main(period="dev"):
    pool = pd.read_parquet("cache/intraday_pool.parquet")
    pool = pool[pool.rk <= 100]
    by_day = {pd.Timestamp(d): set(g) for d, g in pool.groupby("date").symbol}
    allnames = set(pool.symbol)
    files = sorted(glob.glob("cache/mp5min/*.parquet"))
    keep = [f for f in files if DAY(f) in by_day and ((DAY(f) < HOLDOUT_START) == (period == "dev"))]
    assert_sealed([DAY(f) for f in keep])
    jobs = []
    for m, fs in pd.Series(keep, index=[DAY(f).to_period("M") for f in keep]).groupby(level=0):
        first = files.index(fs.iloc[0])
        jobs.append((m, list(fs), files[max(0, first - WARM):first], by_day, allnames))
    t0, rows = time.time(), []
    with Pool(12) as p:
        for i, r in enumerate(p.imap(run_month, jobs)):
            rows += r
            print(f"  {i + 1}/{len(jobs)} months  {len(rows):,} rows  {time.time() - t0:.0f}s", flush=True)
    R = pd.DataFrame(rows)
    assert_sealed(R.date)
    out = f"cache/flip_{period}.parquet"
    R.to_parquet(out, index=False)
    print(f"{len(R):,} rows over {R.date.nunique()} sessions -> {out}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
