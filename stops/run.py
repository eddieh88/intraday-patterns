"""Run the structural-stop study on real 5-minute bars, one calendar month per worker.

  python3 stops/run.py            -> cache/stops_dev.parquet       (development only)
  HOLDOUT_UNLOCK=final-evaluation python3 stops/run.py holdout
                                  -> cache/stops_holdout.parquet   (once, see the prereg)
"""
import glob, sys, time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("stops", "selection")
import sim
from session_summary import session_close
from holdout import HOLDOUT_START, assert_sealed

COLS = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
DAY = lambda f: pd.Timestamp(f.split("_")[-1][:10])


def load(f, names):
    full = pd.read_parquet(f, columns=COLS).dropna(subset=["symbol"])
    close_h = session_close(full)
    d = full[full.symbol.isin(names)]
    t = pd.to_datetime(d.timestamp)
    return d.assign(h=(t.dt.hour + t.dt.minute / 60).values, ts=t.values).sort_values("ts"), close_h


def tails_of(d, close_h):
    """symbol -> (last ATR_N RTH bar ranges, RTH high, RTH low) for the next session."""
    rth = d[(d.h >= 9.5) & (d.h < close_h)]
    out = {}
    for s, g in rth.groupby("symbol"):
        out[s] = ((g.high - g.low).values[-sim.ATR_N:], g.high.max(), g.low.min())
    return out


def run_month(job):
    month, files, prev_file, by_day = job
    allnames = set().union(*by_day.values())
    tails = tails_of(*load(prev_file, allnames)) if prev_file else {}
    trades, days = [], []
    for f in files:
        day = DAY(f)
        d, close_h = load(f, allnames)
        names = by_day.get(day, set())
        for s, g in d[d.symbol.isin(names)].groupby("symbol"):
            if s not in tails:
                continue
            pre = g[g.h < 9.5]; rth = g[(g.h >= 9.5) & (g.h < close_h)]
            o, h, l, c, v = (rth[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
            tr, pdh, pdl = tails[s]
            for t in sim.session_trades(o, h, l, c, v, rth.h.values, pre.high.values, pre.low.values, tr, pdh, pdl):
                t["date"], t["symbol"] = day, s
                trades.append(t)
        tails.update(tails_of(d, close_h))
        days.append(day)
    rng = np.random.default_rng([sim.SEED, month.year, month.month])
    rows = sim.score_month(trades, rng)
    for r, t in zip(rows, trades):
        r["date"], r["symbol"] = t["date"], t["symbol"]
    return rows


def main(period="dev"):
    pool = pd.read_parquet("cache/intraday_pool.parquet")
    pool = pool[pool.rk <= 100]
    by_day = {pd.Timestamp(d): set(g) for d, g in pool.groupby("date").symbol}
    files = sorted(glob.glob("cache/mp5min/*.parquet"))
    keep = [f for f in files if DAY(f) in by_day and ((DAY(f) < HOLDOUT_START) == (period == "dev"))]
    assert_sealed([DAY(f) for f in keep])
    jobs = []
    for m, fs in pd.Series(keep, index=[DAY(f).to_period("M") for f in keep]).groupby(level=0):
        first = files.index(fs.iloc[0])
        jobs.append((m, list(fs), files[first - 1] if first else None, by_day))
    t0, rows = time.time(), []
    with Pool(12) as p:
        for i, r in enumerate(p.imap(run_month, jobs)):
            rows += r
            print(f"  {i + 1}/{len(jobs)} months  {len(rows):,} trades  {time.time() - t0:.0f}s", flush=True)
    R = pd.DataFrame(rows)
    assert_sealed(R.date)
    out = f"cache/stops_{period}.parquet"
    R.to_parquet(out, index=False)
    print(f"{len(R):,} trades over {R.date.nunique()} sessions -> {out}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
