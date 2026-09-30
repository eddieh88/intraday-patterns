"""A StrategyQuant-style strategy generator for spot FX on hourly bars.

A strategy is one entry signal (+ an optional filter), a direction mode, and an exit:
  signal  : one of ~20 indicator conditions, used as mean reversion or as momentum
  filter  : none, a session, a weekday, a volatility regime, or a trend side
  mode    : long only, short only, or both
  exit    : stop a x ATR(14), target b x ATR, time exit after N hours; flat before the
            weekend (Friday 16:00 New York). One position per pair.
Execution: the signal is read at a bar's close and filled at the next bar's open,
buying at the ask and selling at the bid. The stop is checked before the target, and
in the entry bar only the stop counts. No entries 16:00-19:00 New York (the rollover),
nor when the entry spread is above 3x the pair's median. Returns are in bp of the
entry mid.

Every strategy runs on all 8 pairs. The results are monthly sums pooled over pairs,
plus per-pair totals, so in-sample and out-of-sample metrics come from one pass.

`shuffled(h1, seed)` builds the null: the same hourly bars (moves relative to their
open) reordered at random within each month, re-chained into a price path, with the
real spreads left at their clock positions. Volatility and costs are kept; any real
pattern is destroyed.
"""
import itertools
import numpy as np
import pandas as pd
from numba import njit

ATR_N = 14


def hourly(d):
    """1-minute bid/ask frame (explore_own/data.py) -> hourly bars on the New York clock."""
    agg = {}
    for s in ("bid", "ask", "mid"):
        agg.update({f"{s}_open": "first", f"{s}_high": "max", f"{s}_low": "min", f"{s}_close": "last"})
    h = d[list(agg)].resample("1h", label="left", closed="left").agg(agg).dropna()
    return h


def shuffled(h, seed):
    """Null data: bars reordered within each month, re-chained; spreads stay in place."""
    rng = np.random.default_rng(seed)
    rel = np.column_stack([h.mid_high - h.mid_open, h.mid_low - h.mid_open,
                           h.mid_close - h.mid_open, h.mid_open - h.mid_close.shift().fillna(h.mid_open)])
    rel = rel / h.mid_open.values[:, None]
    order = np.arange(len(h))
    for _, idx in pd.Series(np.arange(len(h)), index=h.index).groupby(h.index.to_period("M")):
        order[idx.values] = rng.permutation(idx.values)
    r = rel[order]
    o = np.empty(len(h))
    p = h.mid_open.values[0]
    for i in range(len(h)):
        o[i] = p * (1 + r[i, 3]) if i else p
        p = o[i] * (1 + r[i, 2])
    out = pd.DataFrame(index=h.index)
    out["mid_open"], out["mid_high"], out["mid_low"] = o, o * (1 + r[:, 0]), o * (1 + r[:, 1])
    out["mid_close"] = o * (1 + r[:, 2])
    for c in ("open", "high", "low", "close"):
        half_open = (h.ask_open - h.bid_open).values / 2
        out[f"bid_{c}"] = out[f"mid_{c}"] - half_open
        out[f"ask_{c}"] = out[f"mid_{c}"] + half_open
    return out


def _rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def blocks(h):
    """-> (signals, filters, atr). A signal is a (name, long, short) pair of boolean
    arrays in its mean-reversion sense; the generator also uses it reversed
    (momentum). A filter is (name, mask)."""
    c, hi, lo, o = h.mid_close, h.mid_high, h.mid_low, h.mid_open
    pc = c.shift()
    tr = pd.concat([hi - lo, (hi - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / ATR_N, adjust=False).mean()
    S = []
    for n, lvl in ((2, 10), (5, 25), (14, 30)):
        r = _rsi(c, n)
        S.append((f"rsi{n}<{lvl}", r < lvl, r > 100 - lvl))
    for n in (20, 50, 200):
        m = c.rolling(n).mean()
        S.append((f"below_sma{n}", c < m, c > m))
        S.append((f"cross_sma{n}", (c < m) & (pc >= m.shift()), (c > m) & (pc <= m.shift())))
    for n in (20, 50):
        m, sd = c.rolling(n).mean(), c.rolling(n).std()
        S.append((f"bb{n}_out", c < m - 2 * sd, c > m + 2 * sd))
    for n in (10, 20, 50):
        S.append((f"new_low{n}", c < lo.shift().rolling(n).min(), c > hi.shift().rolling(n).max()))
    for k in (1.5, 2.5):
        big = (hi - lo) > k * atr.shift()
        S.append((f"big_bar{k}", big & (c < o), big & (c > o)))
    for n in (3, 6):
        S.append((f"down{n}bars", (c.diff() < 0).rolling(n).sum() == n, (c.diff() > 0).rolling(n).sum() == n))
    day = (h.index + pd.Timedelta("7h")).normalize()                          # FX day, 17:00 New York
    dc = c.groupby(day).transform("last").groupby(day).first()
    do = o.groupby(day).transform("first").groupby(day).first()
    prev_up = pd.Series((dc > do).shift().values, index=dc.index).reindex(day).values == True    # noqa: E712
    prev_dn = pd.Series((dc < do).shift().values, index=dc.index).reindex(day).values == True    # noqa: E712
    S.append(("prevday_down", pd.Series(prev_dn, index=h.index), pd.Series(prev_up, index=h.index)))
    sd_open = c.groupby(day).transform("first")
    S.append(("down_on_day", c < sd_open - atr, c > sd_open + atr))
    hr, dow = h.index.hour, h.index.dayofweek
    F = [("any", np.ones(len(h), bool)),
         ("asia", (hr >= 19) | (hr < 3)), ("london", (hr >= 3) & (hr < 8)),
         ("newyork", (hr >= 8) & (hr < 12)), ("afternoon", (hr >= 12) & (hr < 16)),
         ("monday", dow == 0), ("friday", dow == 4), ("midweek", (dow >= 1) & (dow <= 3)),
         ("vol_high", (atr > atr.rolling(200).mean()).values), ("vol_low", (atr < atr.rolling(200).mean()).values)]
    m200 = c.rolling(200).mean()
    F.append(("trend_up", (c > m200).values))
    F.append(("trend_down", (c < m200).values))
    sig = [(n, np.nan_to_num(np.asarray(a, float)).astype(bool), np.nan_to_num(np.asarray(b, float)).astype(bool))
           for n, a, b in S]
    return sig, [(n, np.asarray(m, bool)) for n, m in F], atr.values


STOPS, TARGETS, HOLDS = (0.5, 1.0, 1.5, 2.0), (0.5, 1.0, 1.5, 2.0, 3.0), (4, 12, 24)
MODES = ("long", "short", "both")


def catalogue(n_signals, n_filters):
    """Every strategy: (signal, reversed?, filter, mode, stop, target, hold)."""
    return list(itertools.product(range(n_signals), (False, True), range(n_filters), range(3),
                                  STOPS, TARGETS, HOLDS))


@njit(cache=True)
def run_one(go_long, go_short, atr, bo, bh, bl, bc, ao, ah, al, ac, mid_o, ok, fri_end, month,
            a, b, hold, out):
    """Trade one pair; add (sum bp, n, sum bp^2) per month into out[month, :]."""
    n = len(bo)
    i = 0
    while i < n - 1:
        side = 0
        if go_long[i] and ok[i + 1]:
            side = 1
        elif go_short[i] and ok[i + 1]:
            side = -1
        if side == 0 or not (atr[i] > 0):
            i += 1
            continue
        e = i + 1
        px = ao[e] if side == 1 else bo[e]
        stop = px - side * a * atr[i]
        tgt = px + side * b * atr[i]
        j = e
        ex = np.nan
        while j < n:
            if j - e >= hold or (fri_end[j] and j > e):
                ex = bo[j] if side == 1 else ao[j]
                break
            if side == 1:
                if bl[j] <= stop:
                    ex = stop
                    break
                if j > e and bh[j] >= tgt:
                    ex = tgt
                    break
            else:
                if ah[j] >= stop:
                    ex = stop
                    break
                if j > e and al[j] <= tgt:
                    ex = tgt
                    break
            j += 1
        if np.isnan(ex) or j >= n:
            break
        r = side * (ex - px) / mid_o[e] * 1e4
        m = month[e]
        out[m, 0] += r
        out[m, 1] += 1
        out[m, 2] += r * r
        i = j
    return out


def prepare(h):
    """Arrays the engine needs, plus the entry-permission mask."""
    sp = (h.ask_open - h.bid_open).values
    hr = h.index.hour
    ok = (sp <= 3 * np.nanmedian(sp)) & ~((hr >= 16) & (hr < 19))
    fri_end = ((h.index.dayofweek == 4) & (hr >= 16)) | (h.index.dayofweek == 5)
    return dict(bo=h.bid_open.values, bh=h.bid_high.values, bl=h.bid_low.values, bc=h.bid_close.values,
                ao=h.ask_open.values, ah=h.ask_high.values, al=h.ask_low.values, ac=h.ask_close.values,
                mid_o=h.mid_open.values, ok=ok, fri_end=np.asarray(fri_end))
