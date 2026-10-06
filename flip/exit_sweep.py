"""Exploratory: stop-management policies on the silent flip v2 trades (development only).

Same entries as the primary v2 specification, real and fake levels, with each exit
policy applied to the same path. Like E8: if a policy helps real levels and fake
levels alike, it is about exits on any trade, not about the setup.

  python3 flip/exit_sweep.py      -> cache/flip_v2_exits.parquet and a printed table

Every policy keeps the target and the conservative in-bar rule (in the fill bar
only the stop counts). Stop moves use completed bars only.
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
POLICIES = ["fixed", "be_0.5R", "be_1R", "trail_0.5R", "trail_1R",
            "bars1_after1R", "bars3_after1R", "bars6_after1R", "half_at_1R", "exit_11:00", "exit_12:00"]


def exit_policy(o, h, l, c, hh, j, side, fill, stop0, tgt, pol):
    """Gross R of one trade under one policy (1R = |fill - stop0|)."""
    risk = side * (fill - stop0)
    stop, best, banked = stop0, fill, 0.0
    half = pol == "half_at_1R"
    t_end = {"exit_11:00": 11.0, "exit_12:00": 12.0}.get(pol)
    w = 1.0                                                     # share of the position still open
    for i in range(j, len(c)):
        hit_stop = h[i] >= stop if side < 0 else l[i] <= stop
        if hit_stop:
            px = stop if i == j else (max(stop, o[i]) if side < 0 else min(stop, o[i]))
            return banked + w * side * (px - fill) / risk
        if i > j:
            if (side < 0 and l[i] <= tgt) or (side > 0 and h[i] >= tgt):
                px = min(tgt, o[i]) if side < 0 else max(tgt, o[i])
                return banked + w * side * (px - fill) / risk
            if half and w == 1.0 and side * ((l[i] if side < 0 else h[i]) - fill) >= risk:
                banked, w = 0.5, 0.5                            # half off at +1R
        best = min(best, l[i]) if side < 0 else max(best, h[i])
        gain = side * (best - fill) / risk
        if t_end is not None and hh[i] + 5 / 60 >= t_end - 1e-9:
            return banked + w * side * (c[i] - fill) / risk
        # stop moves, applied from the next bar
        new = stop
        if pol == "be_0.5R" and gain >= 0.5 or pol == "be_1R" and gain >= 1:
            new = fill
        elif pol in ("trail_0.5R", "trail_1R"):
            d = (0.5 if pol == "trail_0.5R" else 1.0) * risk
            new = best + d if side < 0 else best - d
        elif pol.startswith("bars") and gain >= 1:
            n = int(pol[4])
            new = h[max(j, i - n + 1):i + 1].max() if side < 0 else l[max(j, i - n + 1):i + 1].min()
        stop = min(stop, new) if side < 0 else max(stop, new)
    return banked + w * side * (c[-1] - fill) / risk


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
        rec = dict(date=r["date"], symbol=r["symbol"], kind=r["kind"], cost=ex["cost"], R_sim=r["R"])
        for pol in POLICIES:
            rec[pol] = exit_policy(o, h, l, c, hh, ex["j"], p["side"], ex["fill"], p["stop"], p["tgt"], pol)
        out.append(rec)
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
    T.to_parquet("cache/flip_v2_exits.parquet", index=False)
    gap = (T.fixed - T.R_sim).abs().max()
    assert gap < 1e-9, f"the fixed policy does not reproduce the simulator (max gap {gap})"
    real, fake = T[T.kind == "real"], T[T.kind == "fake"]
    print(f"{len(real):,} real and {len(fake):,} fake-level trades ({time.time() - t0:.0f}s); net R at {BP} bp\n")
    print(f"{'policy':16s}{'real':>9s}{'t':>7s}{'fake':>9s}{'real-fake':>11s}{'t':>7s}   real by year")
    for pol in POLICIES:
        nr, nf = real[pol] - BP * real.cost, fake[pol] - BP * fake.cost
        m, se, t, _ = clustered(nr, real.date)
        d, _, td = clustered_diff(nr, real.date, nf, fake.date)
        yrs = "  ".join(f"{y}:{v:+.3f}" for y, v in nr.groupby(np.minimum(real.date.dt.year, 2024)).mean().items())
        print(f"{pol:16s}{m:+9.4f}{t:+7.2f}{nf.mean():+9.4f}{d:+11.4f}{td:+7.2f}   {yrs}")


if __name__ == "__main__":
    main()
