"""EXPLORATORY. Per-pair indicators evaluated at the H1 close, from the Darwinex tooltip timing:
groups A/B/C hold 16h15m51s / 13h11m18s / 11h14m53s. Modulo one hour they sit at 15:51 / 11:18 /
14:53, within ~5 minutes: entries on an hour boundary, one common exit a few minutes late. With
the exit at the 17:00 New York rollover delayed ~11-16 min by the spread filter, entries land at
01:00 / 04:00 / 06:00 New York (European morning). Group D (18h48m55s, other leverage) does not fit.

Rule (per pair, same parameters on all pairs): at each H1 close from 00:00 to 09:00 New York,
the first time the condition holds that FX day -> fade it at the next minute; stop S pips, no
target, exit at 17:15 New York (after the rollover spread). Pairs that trigger on the same bar
form a group.
  conditions (fixed threshold X, pips or %):
    open_dist : |close - day open (17:00 NY)| >= X
    prev_dist : |close - previous FX day's close (last mid before 17:00 NY; Friday's on a Monday)| >= X
    h1_move   : |close - previous H1 close| >= X
    h4_move   : |close - close 4 H1 bars ago| >= X
    sma_dist  : |close - SMA20(H1)| >= X        (an Envelopes-style band)
  X: pips {15, 20, 30, 40, 60} or % {0.15, 0.2, 0.3, 0.4, 0.6}; S in {25, 30, 40}
Scored on: return per drawdown, 2022/2021 trade ratio (~5x), scratch rate, group-size mix,
Monday share, win rate, his weekday/timing/P&L fingerprints.

  python3 explore_fx/h1_match.py -> explore_fx/h1_match.csv
"""
import itertools
import multiprocessing as mp
import os
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import data
from weekend_match import walk, his_fingerprints, score, START, END

PAIRS = ["eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]
PIP = {"eurusd": 1e-4, "gbpusd": 1e-4, "audusd": 1e-4, "nzdusd": 1e-4, "usdjpy": 1e-2}
CONDS = ("open_dist", "prev_dist", "h1_move", "h4_move", "sma_dist")
XS = [("pips", v) for v in (15, 20, 30, 40, 60)] + [("pct", v) for v in (0.15, 0.2, 0.3, 0.4, 0.6)]
SS = (25, 30, 40)


def run_pair(pair, conds=CONDS):
    d = data.load(pair, "dev")
    d = d[(d.index >= START - pd.Timedelta("10D")) & (d.index < END)]
    t = d.index.values.astype("int64")
    bo, bh, bl, ao, ah, al = (d[c].values for c in ("bid_open", "bid_high", "bid_low", "ask_open", "ask_high", "ask_low"))
    pip = PIP[pair]
    h = d.mid_close.resample("1h", label="right", closed="right").last().dropna()      # value at the hour's end
    fxday = (h.index + pd.Timedelta("7h")).normalize()
    by_day = d.mid_close.groupby((d.index + pd.Timedelta("7h")).normalize())
    day_open = d.mid_open.groupby((d.index + pd.Timedelta("7h")).normalize()).first().reindex(fxday).values
    prev_close = by_day.last().shift(1).reindex(fxday).values
    feats = {"open_dist": h.values - day_open, "prev_dist": h.values - prev_close, "h1_move": h.diff().values, "h4_move": h.diff(4).values,
             "sma_dist": (h - h.rolling(20).mean()).values}
    hr = h.index.hour
    in_win = (hr >= 0) & (hr <= 9)
    ok_day = ~(((h.index.month == 12) & (h.index.day >= 17)) | ((h.index.month == 1) & (h.index.day <= 5)))
    ok_day &= (h.index >= START) & (h.index.dayofweek < 5)
    rows = []
    for cond in conds:
        f = feats[cond]
        for kind, X in XS:
            thr = X * pip if kind == "pips" else X / 100 * h.values
            fire = in_win & ok_day & (np.abs(f) >= thr)
            seen = set()
            for k in np.flatnonzero(fire):
                day = fxday[k]
                if day in seen:
                    continue
                seen.add(day)
                i = d.index.searchsorted(h.index[k])
                if i >= len(t):
                    continue
                side = -1 if f[k] > 0 else 1
                e = ao[i] if side == 1 else bo[i]
                t_exit = (h.index[k].normalize() + pd.Timedelta("17:15:00")).value
                for S in SS:
                    j, px = walk(t, bo, bh, bl, ao, ah, al, i, side, e - side * S * pip, e + side * 1e6 * pip, t_exit)
                    if j < 0:
                        continue
                    pips = side * (px - e) / pip
                    rows.append((cond, kind, X, S, t[i], t[j], pips, side * (px / e - 1) * 1e4, h.index[k].value))
    df = pd.DataFrame(rows, columns=["cond", "kind", "X", "stop", "t_in", "t_out", "pips", "bp", "bar"])
    df["pair"] = pair
    return df


if __name__ == "__main__":
    cached = "cache/h1_match_trades.parquet"
    if os.path.exists(cached) and "--resim" not in sys.argv:
        trades = pd.read_parquet(cached)
        missing = [c for c in CONDS if c not in set(trades.cond)]
        if missing:                                                    # simulate only new conditions
            with mp.get_context("fork").Pool(5) as pool:
                extra = pool.starmap(run_pair, [(p, tuple(missing)) for p in PAIRS])
            trades = pd.concat([trades] + extra, ignore_index=True)
            trades.to_parquet(cached)
    else:
        with mp.get_context("fork").Pool(5) as pool:
            trades = pd.concat(pool.map(run_pair, PAIRS), ignore_index=True)
        trades.to_parquet(cached)
    iv, his_rate, his_q = his_fingerprints()
    yrs = (END - START).days / 365.25
    out = []
    for key, g0 in trades.groupby(["cond", "kind", "X", "stop"]):
        for trio in itertools.combinations(PAIRS, 3):
            g = g0[g0.pair.isin(trio)]
            if len(g) < 30:
                continue
            r = score(g, iv, his_rate, his_q)
            sizes = g.groupby("bar").size()
            yc = pd.to_datetime(g.t_in).dt.year.value_counts()
            hold_h = (pd.to_datetime(g.t_out) - pd.to_datetime(g.t_in)).dt.total_seconds() / 3600
            out.append(dict(cond=key[0], kind=key[1], X=key[2], stop=key[3], trio="+".join(trio), **r,
                            per_pair_month=len(g) / 3 / yrs / 12,
                            ratio_2022_2021=float(yc.get(2022, 0) / max(yc.get(2021, 1), 1)),
                            scratch=float((g.pips.abs() <= 8).mean()),
                            stopped=float((g.pips <= -g0.stop.iloc[0] + 0.5).mean()),
                            grp1=float((sizes == 1).mean()), grp2=float((sizes == 2).mean()), grp3=float((sizes == 3).mean()),
                            hold_p50=float(hold_h.median())))
    res = pd.DataFrame(out)
    res.to_csv("explore_fx/h1_match.csv", index=False, float_format="%.4f")
    print(f"{len(res)} candidates scored")
