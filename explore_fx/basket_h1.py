"""EXPLORATORY. The dollar-basket trigger (basket_match.py) checked at H1 closes in the European
window that the tooltip timing points to (entries 01:00 / 04:00 / 06:00 New York), exiting at
17:15 New York (the rollover close delayed by the spread filter).

At each H1 close from START_H to END_H New York, the basket = mean of the trio's USD-signed % moves
from the reference (prev_close: last mids before 17:00 NY of the previous FX day, Friday's on a
Monday; day_open: first mids at 17:00 NY). The first close with |basket| >= X -> fade the dollar on
all three pairs at the next minute; stop S pips per pair, no target, exit 17:15 NY.
  window (START_H, END_H) in {(0, 9), (1, 7), (19, 9)}  (19 = from 19:00 the evening before)
  X in {0.15, 0.2, 0.3, 0.4, 0.6}%, S in {25, 30, 40}, reference in {prev_close, day_open}

  python3 explore_fx/basket_h1.py -> explore_fx/basket_h1.csv
"""
import itertools
import multiprocessing as mp
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import basket_match as B
from weekend_match import walk, his_fingerprints, score, START, END

WINDOWS = ((0, 9), (1, 7), (19, 9))
XS, SS = (0.15, 0.2, 0.3, 0.4, 0.6), (25, 30, 40)


def run(trio):
    fr, idx = B.FR, B.IDX
    t = idx.values.astype("int64")
    mids = pd.DataFrame({p: fr[p].mid_close.values for p in trio}, index=idx)
    h = mids.resample("1h", label="right", closed="right").last().dropna()
    fxday_m = (idx + pd.Timedelta("7h")).normalize()
    fxday_h = (h.index + pd.Timedelta("7h")).normalize()
    last = mids.groupby(fxday_m).last()
    first = pd.DataFrame({p: fr[p].mid_open.values for p in trio}, index=idx).groupby(fxday_m).first()
    refs = {"prev_close": last.shift(1).reindex(fxday_h).values, "day_open": first.reindex(fxday_h).values}
    sgn = np.array([B.USD_SIGN[p] for p in trio])
    hr = h.index.hour
    ok = (h.index >= START) & ~(((h.index.month == 12) & (h.index.day >= 17)) | ((h.index.month == 1) & (h.index.day <= 5)))
    rows = []
    for ref_name, ref in refs.items():
        basket = ((h.values / ref - 1) * sgn).mean(1) * 100
        for (a, b) in WINDOWS:
            inw = ((hr >= a) & (hr <= b)) if a < b else ((hr >= a) | (hr <= b))
            for X in XS:
                fire = ok & inw & (np.abs(basket) >= X)
                seen = set()
                for k in np.flatnonzero(fire):
                    if fxday_h[k] in seen:
                        continue
                    seen.add(fxday_h[k])
                    i = idx.searchsorted(h.index[k])
                    if i >= len(t):
                        continue
                    usd_side = -1 if basket[k] > 0 else 1
                    day = h.index[k].normalize() + (pd.Timedelta("1D") if h.index[k].hour >= 17 else pd.Timedelta(0))
                    t_exit = (day + pd.Timedelta("17:15:00")).value
                    for S in SS:
                        for p in trio:
                            f = fr[p]
                            side = usd_side * B.USD_SIGN[p]
                            e = f.ask_open.values[i] if side == 1 else f.bid_open.values[i]
                            j, px = walk(t, f.bid_open.values, f.bid_high.values, f.bid_low.values, f.ask_open.values,
                                         f.ask_high.values, f.ask_low.values, i, side, e - side * S * B.PIP[p],
                                         e + side * 1e6 * B.PIP[p], t_exit)
                            if j < 0:
                                continue
                            rows.append((ref_name, f"{a}-{b}", X, S, t[i], t[j], side * (px - e) / B.PIP[p],
                                         side * (px / e - 1) * 1e4, p))
    df = pd.DataFrame(rows, columns=["ref", "window", "X", "stop", "t_in", "t_out", "pips", "bp", "pair"])
    df["trio"] = "+".join(trio)
    return df


if __name__ == "__main__":
    fr, idx = B.load_all()
    B.FR.update(fr)
    B.IDX = idx
    trios = list(itertools.combinations(B.PAIRS, 3))
    with mp.get_context("fork").Pool(10) as pool:
        trades = pd.concat(pool.map(run, trios), ignore_index=True)
    trades.to_parquet("cache/basket_h1_trades.parquet")
    iv, his_rate, his_q = his_fingerprints()
    yrs = (END - START).days / 365.25
    out = []
    for key, g in trades.groupby(["trio", "ref", "window", "X", "stop"]):
        if len(g) < 30:
            continue
        r = score(g, iv, his_rate, his_q)
        yc = pd.to_datetime(g.t_in).dt.year.value_counts()
        out.append(dict(trio=key[0], ref=key[1], window=key[2], X=key[3], stop=key[4], **r,
                        groups_per_month=g.t_in.nunique() / yrs / 12, scratch=float((g.pips.abs() <= 8).mean()),
                        ratio_2022_2021=float(yc.get(2022, 0) / max(yc.get(2021, 1), 1)),
                        entry_hour_mode=int(pd.to_datetime(g.t_in).dt.hour.mode().iloc[0])))
    res = pd.DataFrame(out)
    res.to_csv("explore_fx/basket_h1.csv", index=False, float_format="%.4f")
    print(f"{len(res)} candidates scored")
