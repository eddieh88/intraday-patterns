"""EXPLORATORY. A shared-trigger version of the open fade, built from the Darwinex tooltips
(09/09/2026 window): the pairs of a group open and close within seconds of each other, and
groups hold 11h15 / 13h11 / 16h16 / 18h49 -> one shared entry signal, a fixed clock close,
entries spread over a window of at least ~7.5h.

Rule: the dollar basket = mean of the USD-pair mids, each signed so + = USD stronger
(EURUSD, GBPUSD, AUDUSD, NZDUSD inverted; USDJPY as is), in % from a reference set at the
FX day's open. In the entry window (17:00 New York + W hours), the first minute the basket's
|move| >= X% (and every pair's spread filter is OK) -> fade the dollar on all chosen pairs at
once. Each pair: stop S pips, no take-profit, close at the clock C. One group per FX day.
  reference: day_open (first mids at 17:00 NY) or prev_close (last mids before 17:00 NY)
  X in {0.10, 0.15, 0.20, 0.30, 0.40}%, W in {6, 8, 10} h, S in {25, 30, 40, none}
  C in {lon17 (17:00 London), ny11 (11:00 NY), ny1655 (16:55 NY)}
  pairs: 3 of the 5 USD majors
Scored on the tooltip groups (hold range 11-19 h, within-group P&L similarity) and the chart
fingerprints (weekday mix, timing, quarterly P&L, frequency, return per drawdown).

  python3 explore_fx/basket_match.py -> explore_fx/basket_match.csv
"""
import itertools
import os
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import data
from weekend_match import walk, his_fingerprints, score, START, END
from spec_search import local_to_ny


def close_after(t, key):
    """The first clock close after t: 17:00 London, 11:00 New York or 16:55 New York."""
    for k in range(3):
        day = t.normalize() + pd.Timedelta(days=k)
        c = {"lon17": local_to_ny(day, 17, 0, "Europe/London"), "ny11": day + pd.Timedelta("11:00:00"),
             "ny1655": day + pd.Timedelta("16:55:00")}[key]
        if c > t:
            return c
    return t + pd.Timedelta("1D")

PAIRS = ["eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]
PIP = {"eurusd": 1e-4, "gbpusd": 1e-4, "audusd": 1e-4, "nzdusd": 1e-4, "usdjpy": 1e-2}
USD_SIGN = {"eurusd": -1, "gbpusd": -1, "audusd": -1, "nzdusd": -1, "usdjpy": 1}
XS, WS, SS, CS = (0.10, 0.15, 0.20, 0.30, 0.40), (6, 8, 10), (25, 30, 40, None), ("lon17", "ny11", "ny1655")


def load_all():
    fr = {}
    for p in PAIRS:
        d = data.load(p, "dev")
        d = d[(d.index >= START - pd.Timedelta("10D")) & (d.index < END)]
        sp = d.spread_mean
        d = d.assign(ok=(sp <= 3 * sp.median()) & (sp <= sp.shift(1).rolling(4, min_periods=1).mean().fillna(np.inf) + 1e-9))
        fr[p] = d
    idx = fr[PAIRS[0]].index
    for p in PAIRS[1:]:
        idx = idx.intersection(fr[p].index)
    return {p: fr[p].reindex(idx) for p in PAIRS}, idx


FR, IDX = {}, None


def run(trio):
    fr, idx = FR, IDX
    mids = np.column_stack([fr[p].mid_open.values for p in trio])
    oks = np.column_stack([fr[p].ok.values for p in trio]).all(1)
    sgn = np.array([USD_SIGN[p] for p in trio])
    t = idx.values.astype("int64")
    fxday = (idx + pd.Timedelta("7h")).normalize()
    bounds = pd.Series(np.arange(len(idx)), index=idx).groupby(fxday).agg(["first", "last"])
    rows, prev_last = [], None
    for _, (i0, i1) in bounds.iterrows():
        open_ny = idx[i0]
        refs = {"day_open": mids[i0]}
        if prev_last is not None:
            refs["prev_close"] = mids[prev_last]
        prev_last = i1
        if open_ny < START or (open_ny.month == 12 and open_ny.day >= 17) or (open_ny.month == 1 and open_ny.day <= 5):
            continue
        for ref_name, ref in refs.items():
            for W in WS:
                b = min(idx.searchsorted(open_ny.normalize() + pd.Timedelta("17:00:00") + pd.Timedelta(hours=W)), i1 + 1)
                seg = mids[i0:b]
                basket = ((seg / ref - 1) * sgn).mean(1) * 100          # + = USD stronger, %
                for X in XS:
                    hit = np.flatnonzero((np.abs(basket) >= X) & oks[i0:b])
                    if not len(hit):
                        continue
                    i = i0 + hit[0]
                    usd_side = -1 if basket[hit[0]] > 0 else 1         # fade: short USD if it rose
                    for C in CS:
                        t_exit = close_after(idx[i], C).value
                        for S in SS:
                            legs = []
                            for k, p in enumerate(trio):
                                f = fr[p]
                                side = usd_side * USD_SIGN[p]            # pair direction that is short/long USD
                                e = f.ask_open.values[i] if side == 1 else f.bid_open.values[i]
                                stop = e - side * (S if S else 1e6) * PIP[p]
                                tgt = e + side * 1e6 * PIP[p]
                                j, px = walk(t, f.bid_open.values, f.bid_high.values, f.bid_low.values, f.ask_open.values,
                                             f.ask_high.values, f.ask_low.values, i, side, stop, tgt, t_exit)
                                if j < 0:
                                    legs = []
                                    break
                                legs.append((p, t[j], side * (px - e) / PIP[p], side * (px / e - 1) * 1e4))
                            for p, tj, pips, bp in legs:
                                rows.append((ref_name, W, X, C, S if S else 0, t[i], tj, pips, bp, p))
    return pd.DataFrame(rows, columns=["ref", "W", "X", "close", "stop", "t_in", "t_out", "pips", "bp", "pair"])


if __name__ == "__main__":
    import multiprocessing as mp
    cached = "cache/basket_match_trades.parquet"
    if os.path.exists(cached) and "--resim" not in sys.argv:
        trades = pd.read_parquet(cached)
    else:
        fr, IDX = load_all()
        FR.update(fr)
        trios = list(itertools.combinations(PAIRS, 3))
        with mp.get_context("fork").Pool(10) as pool:                # forked workers share FR / IDX
            parts = pool.map(run, trios)
        for tr, df in zip(trios, parts):
            df["trio"] = "+".join(tr)
        trades = pd.concat(parts, ignore_index=True)
        trades.to_parquet(cached)
    iv, his_rate, his_q = his_fingerprints()
    yrs = (END - START).days / 365.25
    out = []
    for key, g in trades.groupby(["trio", "ref", "W", "X", "close", "stop"]):
        if len(g) < 30:
            continue
        r = score(g, iv, his_rate, his_q)
        hold_h = (pd.to_datetime(g.t_out) - pd.to_datetime(g.t_in)).dt.total_seconds() / 3600
        grp = g.groupby("t_in").pips
        out.append(dict(trio=key[0], ref=key[1], W=key[2], X=key[3], close=key[4], stop=key[5], **r,
                        groups_per_month=g.t_in.nunique() / yrs / 12,
                        hold_p10=float(hold_h.quantile(0.1)), hold_p90=float(hold_h.quantile(0.9)),
                        within_group_sd=float(grp.std().median()), avg_pips=float(g.pips.mean()),
                        ratio_2022_2021=float(pd.to_datetime(g.t_in).dt.year.value_counts().get(2022, 0) /
                                              max(pd.to_datetime(g.t_in).dt.year.value_counts().get(2021, 1), 1))))
    res = pd.DataFrame(out)
    res.to_csv("explore_fx/basket_match.csv", index=False, float_format="%.4f")
    print(f"{len(res)} candidates scored")
