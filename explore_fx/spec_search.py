"""EXPLORATORY. A narrow search built from the behavioural spec (the doc's "Working spec",
after the expert's reading of the Darwinex pages), scored on the spec's numbers first and on
the chart's timing only as a tie-breaker. Spot FX bid/ask (HistData), 2018-01 .. 2026-07.

Rule: a reference price is set at a fixed time; within a 6-hour session window, the first
touch of a fixed displacement from it (pips or %) is faded at once (no confirmation); a fixed
stop, NO take-profit, and a fixed clock close. One trade per pair per day. No entries
17 Dec - 5 Jan (his book's holiday shutdown).
  reference: day_open (first mid at 17:00 New York), week_open (Sunday 17:00), prev_close
             (last mid before 17:00 New York), london_open (first mid at 08:00 London)
  window   : asia (17:00-23:00 NY), london (08:00-14:00 London), newyork (08:00-14:00 NY);
             london_open is only paired with the london window
  displacement: 20, 30, 40, 50, 60, 80 pips or 0.2, 0.3, 0.4, 0.6, 0.8%
  close    : 16:55 New York, 21:00 UTC, 22:00 UTC, 17:00 London (the first after entry)
  stop     : 25, 30, 40 pips
  pairs    : 3 of the 5 USD majors we hold (EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY)

Spec targets: 2022/2021 trade-rate ratio ~5x; scratch rate (|pips| <= 8) ~70%; stop rate ~12%;
return per max drawdown ~1x a year; 4-5 trades per pair per month.

  python3 explore_fx/spec_search.py -> explore_fx/spec_search.csv
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
REFS = ("day_open", "week_open", "prev_close", "london_open")
WINDOWS = ("asia", "london", "newyork")
DISPS = [("pips", v) for v in (20, 30, 40, 50, 60, 80)] + [("pct", v) for v in (0.2, 0.3, 0.4, 0.6, 0.8)]
CLOSES = ("ny1655", "utc21", "utc22", "lon17")
STOPS = (25, 30, 40)
NY, UTC, LON = "America/New_York", "UTC", "Europe/London"


def local_to_ny(day_ny, hh, mm, tz):
    """The NY-naive timestamp of hh:mm in timezone tz on the calendar date of day_ny."""
    t = pd.Timestamp(day_ny.date()) + pd.Timedelta(hours=hh, minutes=mm)
    return t.tz_localize(tz).tz_convert(NY).tz_localize(None)


def windows_for(open_ny):
    """FX day starting at open_ny (17:00 NY) -> {window: (start, end)} in NY-naive time."""
    nxt = open_ny + pd.Timedelta("1D")
    lon0 = local_to_ny(nxt, 8, 0, LON)
    ny0 = local_to_ny(nxt, 8, 0, NY)
    return {"asia": (open_ny, open_ny + pd.Timedelta("6h")),
            "london": (lon0, lon0 + pd.Timedelta("6h")),
            "newyork": (ny0, ny0 + pd.Timedelta("6h"))}


def close_after(t, key):
    for k in range(3):
        day = t.normalize() + pd.Timedelta(days=k)
        c = {"ny1655": day + pd.Timedelta("16:55:00"),
             "utc21": local_to_ny(day, 21, 0, UTC), "utc22": local_to_ny(day, 22, 0, UTC),
             "lon17": local_to_ny(day, 17, 0, LON)}[key]
        if c > t:
            return c
    return t + pd.Timedelta("1D")


def run_pair(pair):
    d = data.load(pair, "dev")
    d = d[(d.index >= START - pd.Timedelta("10D")) & (d.index < END)]
    sp = d.spread_mean
    ok = ((sp <= 3 * sp.median()) & (sp <= sp.shift(1).rolling(4, min_periods=1).mean().fillna(np.inf) + 1e-9)).values
    idx = d.index
    t = idx.values.astype("int64")
    mid = d.mid_open.values
    bo, bh, bl, ao, ah, al = (d[c].values for c in ("bid_open", "bid_high", "bid_low", "ask_open", "ask_high", "ask_low"))
    pip = PIP[pair]
    fxday = (idx + pd.Timedelta("7h")).normalize()
    bounds = pd.Series(np.arange(len(idx)), index=idx).groupby(fxday).agg(["first", "last"])
    rows = []
    week_ref = np.nan
    prev_last = None
    for day, (i0, i1) in bounds.iterrows():
        open_ny = idx[i0]
        if idx[i0].dayofweek == 6 or (prev_last is not None and idx[i0] - idx[prev_last] > pd.Timedelta("36h")):
            week_ref = mid[i0]
        refs = {"day_open": mid[i0], "week_open": week_ref,
                "prev_close": d.mid_close.values[prev_last] if prev_last is not None else np.nan}
        lon_open = idx.searchsorted(local_to_ny(open_ny + pd.Timedelta("1D"), 8, 0, LON))
        refs["london_open"] = mid[lon_open] if i0 <= lon_open <= i1 else np.nan
        prev_last = i1
        if open_ny < START or (open_ny.month == 12 and open_ny.day >= 17) or (open_ny.month == 1 and open_ny.day <= 5):
            continue
        W = windows_for(open_ny.normalize() + pd.Timedelta("17:00:00"))
        for ref_name, ref in refs.items():
            if np.isnan(ref):
                continue
            for wname in WINDOWS:
                if ref_name == "london_open" and wname != "london":
                    continue
                a, b = idx.searchsorted(W[wname][0]), idx.searchsorted(W[wname][1])
                a = max(a, i0)
                b = min(b, i1 + 1)
                if ref_name == "london_open":
                    a = max(a, lon_open + 1)
                if b <= a:
                    continue
                dist_pips = (mid[a:b] - ref) / pip
                dist_pct = (mid[a:b] / ref - 1) * 100
                okk = ok[a:b]
                for kind, v in DISPS:
                    dd = dist_pips if kind == "pips" else dist_pct
                    hit = np.flatnonzero((np.abs(dd) >= v) & okk)
                    if not len(hit):
                        continue
                    i = a + hit[0]
                    side = -1 if mid[i] > ref else 1
                    e = ao[i] if side == 1 else bo[i]
                    for ck, S in itertools.product(CLOSES, STOPS):
                        stop = e - side * S * pip
                        tgt = e + side * 1e6 * pip                     # no take-profit
                        j, px = walk(t, bo, bh, bl, ao, ah, al, i, side, stop, tgt, close_after(idx[i], ck).value)
                        if j < 0:
                            continue
                        pips = side * (px - e) / pip
                        rows.append((ref_name, wname, kind, v, ck, S, t[i], t[j], pips, side * (px / e - 1) * 1e4,
                                     abs(px - stop) < 1e-12))
    df = pd.DataFrame(rows, columns=["ref", "window", "kind", "disp", "close", "stop", "t_in", "t_out", "pips", "bp", "stopped"])
    df["pair"] = pair
    return df


GROUPS = {}


def score_job(args):
    key, trios = args
    iv, his_rate, his_q = his_fingerprints()
    yrs = (END - START).days / 365.25
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
        yc = tin.dt.year.value_counts()
        r.update(per_pair_month=len(g) / 3 / yrs / 12,
                 ratio_2022_2021=float(yc.get(2022, 0) / max(yc.get(2021, 1), 1)),
                 scratch=float((g.pips.abs() <= 8).mean()), stop_rate=float(g.stopped.mean()),
                 avg_win_pips=float(g.pips[g.pips > 8].mean()) if (g.pips > 8).any() else 0.0)
        out.append(dict(ref=key[0], window=key[1], kind=key[2], disp=key[3], close=key[4], stop=key[5],
                        pairs="+".join(trio), **r))
    return out


if __name__ == "__main__":
    cached = "cache/spec_search_trades.parquet"
    if os.path.exists(cached) and "--resim" not in sys.argv:
        trades = pd.read_parquet(cached)
    else:
        with mp.get_context("fork").Pool(5) as pool:
            trades = pd.concat(pool.map(run_pair, PAIRS), ignore_index=True)
        trades.to_parquet(cached)
    keys = ["ref", "window", "kind", "disp", "close", "stop"]
    for key, g in trades.groupby(keys + ["pair"]):
        GROUPS[(tuple(key[:6]), key[6])] = g
    configs = sorted({k for k, _ in GROUPS})
    trios = list(itertools.combinations(PAIRS, 3))
    with mp.get_context("fork").Pool(14) as pool:
        res = pool.map(score_job, [(k, trios) for k in configs])
    out = pd.DataFrame([r for part in res for r in part])
    out.to_csv("explore_fx/spec_search.csv", index=False, float_format="%.4f")
    print(f"{len(out)} candidates scored")
