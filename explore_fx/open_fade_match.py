"""EXPLORATORY. The "fade the distance from the previous close, shortly after the daily open"
family, scored against the posted chart and the Darwinex book statistics. Spot FX bid/ask
(HistData), 2018-01 .. 2026-07.

Why this family (see the doc's forensics + the expert's reading of the Darwinex pages):
  - his deal weekdays (Mon 13, Tue 2, Wed 3, Thu 6, Fri 5 of 29 labels) are matched by a
    fixed-pip distance from the previous 17:00 New York close, checked ~2h after the open:
    on Mondays that distance includes the weekend gap (weekday log-likelihood -41.97 vs -40.83
    for a perfect fit and -46.67 for uniform)
  - trades come as triplets (3 pairs opened together, closed together after ~16h): a common
    clock, a time exit
  - entries are taken on touch (his entry timing ranks 11 of 11 on Darwinex), a fixed bracket
    of about +-30 pips, one trade per pair every 2-3 weeks, ~5x denser in volatile years

Rule: FX day starts 17:00 New York. ref = previous day's last mid before 17:00.
  entry modes: "touch_19" / "touch_23": the first minute from 17:00 to 19:00 / 23:00 with
               |mid - ref| >= X pips AND the spread filter OK -> fade at that minute
               "at_19": check once at 19:00 (first spread-OK minute within 30 min)
  stop S pips, target rr x S, time exit after H hours, one trade per pair per day.
  X in {15, 20, 25, 30, 40} pips, S in {20, 30, 40}, rr in {0.75, 1.0}, H in {12, 16, 18}
Execution at bid/ask; stop checked before target; no target in the entry minute.

  python3 explore_fx/open_fade_match.py -> explore_fx/open_fade_match.csv
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
from weekend_match import walk, his_fingerprints, score, PAIRS, START, END

PIP = {"eurusd": 1e-4, "gbpusd": 1e-4, "audusd": 1e-4, "nzdusd": 1e-4, "usdjpy": 1e-2,
       "eurgbp": 1e-4, "eurchf": 1e-4, "audnzd": 1e-4}
MODES = ("touch_19", "touch_23", "at_19")
XS, SS, RRS, HS = (15, 20, 25, 30, 40), (20, 30, 40), (0.75, 1.0), (12, 16, 18)


def run_pair(pair):
    d = data.load(pair, "dev")
    d = d[(d.index >= START - pd.Timedelta("7D")) & (d.index < END)]
    sp = d.spread_mean
    ok = ((sp <= 3 * sp.median()) & (sp <= sp.shift(1).rolling(4, min_periods=1).mean().fillna(np.inf) + 1e-9)).values
    t = d.index.values.astype("int64")
    bo, bh, bl = d.bid_open.values, d.bid_high.values, d.bid_low.values
    ao, ah, al = d.ask_open.values, d.ask_high.values, d.ask_low.values
    mid = d.mid_open.values
    idx = d.index
    fxday = (idx + pd.Timedelta("7h")).normalize()
    starts = pd.Series(np.arange(len(idx)), index=idx).groupby(fxday).agg(["first", "last"])
    pip = PIP[pair]
    rows = []
    days = starts.index
    for k in range(1, len(days)):
        i0, i1 = starts.iloc[k]["first"], starts.iloc[k]["last"]
        ref = d.mid_close.values[starts.iloc[k - 1]["last"]]
        open_t = idx[i0]
        if open_t < START or idx[starts.iloc[k - 1]["last"]] < open_t - pd.Timedelta("3D"):
            continue
        dist = (mid[i0:i1 + 1] - ref) / pip
        okk = ok[i0:i1 + 1]
        tt = idx[i0:i1 + 1]
        cand = {}
        for mode, end_h in (("touch_19", 2), ("touch_23", 6)):
            lim = tt.searchsorted(open_t + pd.Timedelta(hours=end_h))
            cand[mode] = (dist[:lim], okk[:lim], 0)
        j19 = tt.searchsorted(tt[0].normalize() + pd.Timedelta("19:00:00") if tt[0].hour < 19 else tt[0])
        cand["at_19"] = (dist[j19:j19 + 30], okk[j19:j19 + 30], j19)
        for mode in MODES:
            dd, oo, off = cand[mode]
            for X in XS:
                hit = np.flatnonzero((np.abs(dd) >= X) & oo)
                if mode == "at_19":
                    hit = hit[:1] if len(hit) and np.abs(dd[0]) >= X else hit[:0]
                if not len(hit):
                    continue
                i = i0 + off + hit[0]
                side = -1 if mid[i] > ref else 1
                e = ao[i] if side == 1 else bo[i]
                for S, rr, H in itertools.product(SS, RRS, HS):
                    stop, tgt = e - side * S * pip, e + side * rr * S * pip
                    t_exit = (idx[i] + pd.Timedelta(hours=H)).value
                    j, px = walk(t, bo, bh, bl, ao, ah, al, i, side, stop, tgt, t_exit)
                    if j < 0:
                        continue
                    rows.append((mode, X, S, rr, H, t[i], t[j], side * (px - e) / pip, side * (px / e - 1) * 1e4))
    df = pd.DataFrame(rows, columns=["mode", "X", "S", "rr", "H", "t_in", "t_out", "pips", "bp"])
    df["pair"] = pair
    return df


GROUPS = {}


def score_job(args):
    key, trios = args
    iv, his_rate, his_q = his_fingerprints()
    out = []
    for trio in trios:
        parts = [GROUPS[(key, p)] for p in trio if (key, p) in GROUPS]
        if not parts:
            continue
        g = pd.concat(parts)
        if len(g) < 30:
            continue
        r = score(g, iv, his_rate, his_q)
        tin = pd.to_datetime(g.t_in)
        per_pair_yr = len(g) / 3 / ((END - START).days / 365.25)
        dens = tin.dt.year.value_counts()
        r.update(per_pair_yr=per_pair_yr, avg_win_pips=float(g.pips[g.pips > 0].mean()),
                 avg_loss_pips=float(g.pips[g.pips <= 0].mean()),
                 y2022_vs_2021=float(dens.get(2022, 0) / max(dens.get(2021, 1), 1)))
        out.append(dict(mode=key[0], X=key[1], S=key[2], rr=key[3], H=key[4], pairs="+".join(trio), **r))
    return out


if __name__ == "__main__":
    cached = "cache/open_fade_trades.parquet"
    if os.path.exists(cached) and "--resim" not in sys.argv:
        trades = pd.read_parquet(cached)
    else:
        with mp.get_context("fork").Pool(4) as pool:
            trades = pd.concat(pool.map(run_pair, PAIRS), ignore_index=True)
        trades.to_parquet(cached)
    keys = ["mode", "X", "S", "rr", "H"]
    for key, g in trades.groupby(keys + ["pair"]):
        GROUPS[(tuple(key[:5]), key[5])] = g
    configs = sorted({k for k, _ in GROUPS})
    trios = list(itertools.combinations(PAIRS, 3))
    with mp.get_context("fork").Pool(14) as pool:
        res = pool.map(score_job, [(k, trios) for k in configs])
    out = pd.DataFrame([r for part in res for r in part])
    out.to_csv("explore_fx/open_fade_match.csv", index=False, float_format="%.4f")
    print(f"{len(out)} candidates scored")
