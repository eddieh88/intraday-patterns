"""Two FX strategy families traded on real spot bid/ask (explore_own/data.py frames).
Buys fill at the ask and sells at the bid. Returns are in bp of the entry mid.

Spread filter (his tip): enter only if the entry minute's mean spread is <= `cap`
pips and <= the mean of the previous 4 minutes (a 240-second average).

night(d, ...)  5-minute Bollinger(n, k) on mid closes; a close outside the band is faded
               at the next minute's open, for bars closing between `start` and `last`
               New York. exit="mid": target the middle band, stop 2x that distance
               beyond (negative skew). exit="bracket": stop and target both at the
               band displacement (1:1). Flat at `flat`. One position at a time.
gap(d, ...)    at the Sunday reopen (17:00 New York) + `wait` minutes, fade the weekend
               gap from Friday's last mid if it exceeds x%. Stop s%, target rr x s%.
               Flat Monday 16:45.
Within a minute the stop is checked before the target.
"""
import numpy as np
import pandas as pd


def spread_ok(d, cap):
    sp = d.spread_mean
    return (sp <= cap) & (sp <= sp.shift(1).rolling(4, min_periods=1).mean().fillna(np.inf) + 1e-9)


def _walk(d, i, side, stop, tgt, flat_t):
    """From minute i (entry at its open), walk to the exit. -> (exit index, exit price, why)"""
    ts = d.index
    BL, AH, BH, AL = d.bid_low.values, d.ask_high.values, d.bid_high.values, d.ask_low.values
    BO, AO = d.bid_open.values, d.ask_open.values
    for j in range(i, len(ts)):
        if ts[j] >= flat_t:
            return j, (BO[j] if side == 1 else AO[j]), "time"
        if side == 1:
            if BL[j] <= stop:
                return j, stop, "stop"
            if j > i and BH[j] >= tgt:
                return j, tgt, "target"
        else:
            if AH[j] >= stop:
                return j, stop, "stop"
            if j > i and AL[j] <= tgt:
                return j, tgt, "target"
    return None


def _flat_after(t, hhmm):
    f = t.normalize() + pd.Timedelta(hhmm + ":00")
    return f if f > t else f + pd.Timedelta("1D")


def night(d, n=20, k=2.0, start="20:00", last="01:00", flat="02:00", exit="mid", cap=2.0):
    b = d.mid_close.resample("5min", label="left", closed="left").last().dropna()
    m, sd = b.rolling(n).mean(), b.rolling(n).std()
    side = np.where(b > m + k * sd, -1, np.where(b < m - k * sd, 1, 0))
    close_t = b.index + pd.Timedelta("5min")
    tod = close_t.hour * 60 + close_t.minute
    s0, s1 = (int(x[:2]) * 60 + int(x[3:]) for x in (start, last))
    win = (tod >= s0) | (tod <= s1)
    dow = close_t.dayofweek
    nightly = np.where(tod >= s0, (dow <= 3) | (dow == 6), dow <= 4)
    sig = pd.DataFrame({"t": close_t, "side": side, "mid": m.values, "c": b.values}, index=b.index)
    sig = sig[win & nightly & (side != 0) & ~np.isnan(m.values)]
    ok = spread_ok(d, cap).values
    ts, AO, BO, MO = d.index, d.ask_open.values, d.bid_open.values, d.mid_open.values
    out, free = [], pd.Timestamp.min
    for r in sig.itertuples():
        if r.t < free:
            continue
        i = ts.searchsorted(r.t)
        if i >= len(ts) or ts[i] - r.t > pd.Timedelta("3min") or not ok[i]:
            continue
        e = AO[i] if r.side == 1 else BO[i]
        dist = abs(r.c - r.mid)
        if exit == "mid":
            tgt, stop = r.mid, e - r.side * 2 * abs(r.mid - e)
            if r.side * (tgt - e) <= 0:
                continue
        else:
            tgt, stop = e + r.side * dist, e - r.side * dist
        res = _walk(d, i, r.side, stop, tgt, _flat_after(ts[i], flat))
        if res is None:
            break
        j, px, why = res
        out.append(dict(t_in=ts[i], t_out=ts[j], side=r.side, why=why,
                        bp=r.side * (px - e) / MO[i] * 1e4, spread_bp=(AO[i] - BO[i]) / MO[i] * 1e4))
        free = ts[j]
    return pd.DataFrame(out)


def gap(d, x=0.2, s=0.4, rr=1.0, wait=30, cap=5.0):
    ts = d.index
    ok = spread_ok(d, cap).values
    AO, BO, MO, MC = d.ask_open.values, d.bid_open.values, d.mid_open.values, d.mid_close.values
    out = []
    for sun in pd.DatetimeIndex(ts.normalize().unique())[pd.DatetimeIndex(ts.normalize().unique()).dayofweek == 6]:
        t0 = sun + pd.Timedelta("17:00:00") + pd.Timedelta(minutes=wait)
        fri_end = sun - pd.Timedelta("2D") + pd.Timedelta("17:00:00")
        pf = ts.searchsorted(fri_end) - 1
        i = ts.searchsorted(t0)
        if pf < 0 or i >= len(ts) or ts[pf] < fri_end - pd.Timedelta("1h") or ts[i] - t0 > pd.Timedelta("30min"):
            continue
        while i < len(ts) and not ok[i] and ts[i] - t0 < pd.Timedelta("2h"):
            i += 1
        if i >= len(ts) or not ok[i]:
            continue
        g = MO[i] / MC[pf] - 1
        if abs(g) <= x / 100:
            continue
        side = -int(np.sign(g))
        e = AO[i] if side == 1 else BO[i]
        stop, tgt = e * (1 - side * s / 100), e * (1 + side * rr * s / 100)
        res = _walk(d, i, side, stop, tgt, sun + pd.Timedelta("1D") + pd.Timedelta("16:45:00"))
        if res is None:
            break
        j, px, why = res
        out.append(dict(t_in=ts[i], t_out=ts[j], side=side, why=why, gap_pct=g * 100,
                        bp=side * (px - e) / MO[i] * 1e4, spread_bp=(AO[i] - BO[i]) / MO[i] * 1e4))
    return pd.DataFrame(out)
