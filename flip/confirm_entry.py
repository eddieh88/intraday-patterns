"""Exploratory: a confirmed entry for the silent flip v2 (development only).

In his description the third 15-minute candle (10:00-10:15) moves the same way as
the silent candle. He enters on the touch, before that candle closes, so its color
cannot be a filter for the touch entry without look-ahead. The legitimate version
waits:

  confirmed: the third candle closes beyond candle 2's extreme (below its low for a
  short) and has the silent candle's color. Enter at that close, 10:15, with the same
  stop and target. No trade if the stop traded during the third candle.

Reported for real and fake levels, by year. Also, as a diagnostic only (it uses the
third candle's close, which the touch entry cannot know): the touch entry split by
whether the third candle confirmed.

  python3 flip/confirm_entry.py
"""
import glob, time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("flip", "selection")
import sim
import run
from flip_stats import clustered, clustered_diff
from holdout import HOLDOUT_START, assert_sealed

BP = 3


def month(job):
    sim.GRID_V2 = [sim.PRIMARY_V2]
    captured = []
    base = sim.execute

    def execute(o, h, l, c, hh, p, win_end=sim.WIN_END, starts=None, trail=False):
        ex = base(o, h, l, c, hh, p, win_end, starts, trail)
        if ex is not None and win_end == sim.WIN_END and not trail and starts is None:
            captured.append((o, h, l, c, hh, p, ex))
        return ex

    sim.execute = execute
    rows = run.run_month(job)
    out = []
    for r, (o, h, l, c, hh, p, ex) in zip(rows, captured):
        side, trig, stop, tgt = p["side"], p["trig"], p["stop"], p["tgt"]
        O, H, L, C, starts = sim.bars15(o, h, l, c, hh)
        rec = dict(date=r["date"], symbol=r["symbol"], kind=r["kind"], R_touch=ex["R"], c_touch=ex["cost"],
                   confirmed=False, R_conf=np.nan, c_conf=np.nan)
        if len(O) > 3:
            beyond = C[2] < trig if side < 0 else C[2] > trig
            color = (C[2] < O[2]) if side < 0 else (C[2] > O[2])
            stopped = H[2] >= stop if side < 0 else L[2] <= stop
            rec["confirmed"] = bool(beyond and color and not stopped)
            j = starts[3]                                   # first 5-minute bar after 10:15
            fill = C[2]
            if rec["confirmed"] and side * (tgt - fill) > 0 and j < len(c):
                R, _ = sim.exits(o, h, l, c, j, side, fill, stop, tgt)
                rec["R_conf"], rec["c_conf"] = R, 1e-4 * fill / (side * (fill - stop))
        out.append(rec)
    return out


def line(name, x, gx, y=None, gy=None):
    m, se, t, n = clustered(x, gx)
    s = f"  {name:34s} n {n:5,}  net {m:+.4f} (t {t:+.2f})"
    if y is not None:
        d, _, td = clustered_diff(x, gx, y, gy)
        s += f"   fake {np.nanmean(y):+.4f}   real-fake {d:+.4f} (t {td:+.2f})"
    return s


def main():
    pool = pd.read_parquet("cache/intraday_pool.parquet")
    pool = pool[pool.rk <= 100]
    by_day = {pd.Timestamp(d): set(g) for d, g in pool.groupby("date").symbol}
    allnames = set(pool.symbol)
    files = sorted(glob.glob("cache/mp5min/*.parquet"))
    keep = [f for f in files if run.DAY(f) in by_day and run.DAY(f) < HOLDOUT_START]
    jobs = []
    for m, fs in pd.Series(keep, index=[run.DAY(f).to_period("M") for f in keep]).groupby(level=0):
        first = files.index(fs.iloc[0])
        jobs.append((m, list(fs), files[max(0, first - run.WARM):first], by_day, allnames, 2))
    t0 = time.time()
    with Pool(12) as p:
        T = pd.DataFrame([r for m in p.map(month, jobs) for r in m])
    assert_sealed(T.date)
    T.to_parquet("cache/flip_v2_confirm.parquet", index=False)
    real, fake = T[T.kind == "real"], T[T.kind == "fake"]
    print(f"{len(real):,} real and {len(fake):,} fake-level touch trades ({time.time() - t0:.0f}s); net R at {BP} bp\n")
    print(f"third candle confirms (closes beyond the trigger, silent color): "
          f"real {real.confirmed.mean():.1%}, fake {fake.confirmed.mean():.1%}\n")
    rc, fc = real[real.confirmed & real.R_conf.notna()], fake[fake.confirmed & fake.R_conf.notna()]
    print("CONFIRMED ENTRY at the 10:15 close (tradable)")
    print(line("confirmed entry", rc.R_conf - BP * rc.c_conf, rc.date, fc.R_conf - BP * fc.c_conf, fc.date))
    for y, g in rc.groupby(np.minimum(rc.date.dt.year, 2024)):
        print(f"      {y}: n {len(g):4d}  net {(g.R_conf - BP * g.c_conf).mean():+.4f}")
    print("\nTOUCH ENTRY split by the third candle (diagnostic: uses its close, not tradable as a filter)")
    for flag, name in ((True, "touch, third candle confirmed"), (False, "touch, third candle did not")):
        a, b = real[real.confirmed == flag], fake[fake.confirmed == flag]
        print(line(name, a.R_touch - BP * a.c_touch, a.date, b.R_touch - BP * b.c_touch, b.date))


if __name__ == "__main__":
    main()
