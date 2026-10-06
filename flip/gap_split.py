"""Exploratory: silent flip v2 trades split by where candle 1 opened (development only).

u = how far the 09:30 open sits from the tested side of yesterday's range toward the
opposite side: 0 at the tested range level, 1 at the opposite one (the target).
For a long tested at RL, u = (open - RL) / (RH - RL); for a short, u = (RH - open) / (RH - RL).

  u >= 0.8   opened near or beyond the opposite level: gap-and-reverse, the whole
             range in one candle (his PFE on 2026-09-03; GM on 2021-06-02)
  0.2-0.8    opened inside the range: a push into the level (his NVDA, UBER)
  u < 0.2    opened at or past the tested level already

  python3 flip/gap_split.py
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
    base_ex, base_pat = sim.execute, sim.pattern

    def pattern(O, H, L, C, atr, RH, RL, FH, FL, sp):
        p = base_pat(O, H, L, C, atr, RH, RL, FH, FL, sp)
        if p is not None:
            p.update(RH=RH, RL=RL, open=O[0])
        return p

    def execute(o, h, l, c, hh, p, win_end=sim.WIN_END, starts=None, trail=False):
        ex = base_ex(o, h, l, c, hh, p, win_end, starts, trail)
        if ex is not None and win_end == sim.WIN_END and not trail and starts is None:
            captured.append((p, ex))
        return ex

    sim.pattern, sim.execute = pattern, execute
    rows = run.run_month(job)
    out = []
    for r, (p, ex) in zip(rows, captured):
        width = p["RH"] - p["RL"]
        u = ((p["open"] - p["RL"]) if p["side"] > 0 else (p["RH"] - p["open"])) / width if width > 0 else np.nan
        out.append(dict(date=r["date"], kind=r["kind"], u=u, net=ex["R"] - BP * ex["cost"], tgt_R=ex["tgt_R"]))
    return out


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
    T.to_parquet("cache/flip_v2_gap.parquet", index=False)
    T["where"] = pd.cut(T.u, [-np.inf, 0.2, 0.8, np.inf], labels=["at/past tested level", "inside: push", "gap-and-reverse"])
    print(f"{(T.kind == 'real').sum():,} real and {(T.kind == 'fake').sum():,} fake trades ({time.time() - t0:.0f}s); net R at {BP} bp\n")
    for w, g in T.groupby("where", observed=True):
        r, f = g[g.kind == "real"], g[g.kind == "fake"]
        m, se, t, n = clustered(r.net, r.date)
        d, _, td = clustered_diff(r.net, r.date, f.net, f.date)
        yrs = "  ".join(f"{y}:{v:+.3f}" for y, v in r.net.groupby(np.minimum(r.date.dt.year, 2024)).mean().items())
        print(f"  {w:22s} real n {n:4d} ({n / (T.kind == 'real').sum():.0%})  net {m:+.4f} (t {t:+.2f})  "
              f"median target {r.tgt_R.median():.1f}R | fake {f.net.mean():+.4f}  real-fake {d:+.4f} (t {td:+.2f})")
        print(f"  {'':22s} {yrs}")


if __name__ == "__main__":
    main()
