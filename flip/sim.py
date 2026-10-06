"""The silent flip. Rules: prereg/silent_flip.md.

Pure functions on arrays, shared by run.py (real bars), random_walk_check.py and
the tests.

  bars15()      15-minute bars from one session's 5-minute RTH bars
  flip_levels() FH / FL: the latest swing beyond RH / RL from before yesterday
  pattern()     candles 1 and 2 against the levels -> trigger, stop, target
  execute()     the stop order on 5-minute bars, then the exits
  name_day()    everything for one name on one day: real, fake levels, random entry
"""
import itertools
from dataclasses import dataclass

import numpy as np

SWING_K, LOOKBACK, ATR_N = 2, 20, 14
BRK, STOP_BUF = 0.1, 0.1                    # x ATR15
WIN_END = 10 + 25 / 60                      # last 5-minute bar stamp the stop order is live
WIN_END_LATE = 10 + 55 / 60                 # reported variant: live to 11:00
N_DRAWS, SEED = 20, 7


@dataclass(frozen=True)
class Spec:
    strong: float = 1.0                     # candle-1 range, x ATR15
    body: float = 0.6                       # candle-1 body share of its range
    tol: float = 0.25                       # how near the level counts as a test, x unit
    target: str = "opp"                     # opp | near | 2R
    unit: str = "atr"                       # v1: tolerances in ATR15; v2: "c1" = candle-1 range
    flat: float = 0.0                       # v2: candle 2 may close this much (x candle-1 range) the wrong way


PRIMARY = Spec()
GRID = [Spec(*x) for x in itertools.product((0.75, 1.0, 1.5), (0.5, 0.6, 0.7),
                                            (0.1, 0.25, 0.5), ("opp", "near", "2R"))]

# version 2 (prereg/silent_flip_v2.md): within-session flip swings, tolerances in candle-1 units
PRIMARY_V2 = Spec(1.0, 0.6, 0.10, "opp", "c1", 0.05)
GRID_V2 = [Spec(1.0, b, t, g, "c1", f) for b, t, f, g in itertools.product(
    (0.5, 0.6, 0.7), (0.05, 0.10, 0.20), (0.0, 0.05, 0.10), ("opp", "near", "2R"))]


def bars15(o, h, l, c, hh):
    """-> (O, H, L, C, start index of each 15-minute bar in the 5-minute arrays)."""
    k = np.floor((hh - 9.5) * 4 + 1e-9).astype(int)
    starts = np.r_[0, np.flatnonzero(np.diff(k)) + 1]
    ends = np.r_[starts[1:], len(k)]
    O = o[starts]; C = c[ends - 1]
    H = np.array([h[a:b].max() for a, b in zip(starts, ends)])
    L = np.array([l[a:b].min() for a, b in zip(starts, ends)])
    return O, H, L, C, starts


def flip_levels(H, L, sess, yday, RH, RL, within=False):
    """Latest swing high above RH and swing low below RL, in sessions before `yday`.

    H, L, sess: 15-minute bars of the stored sessions, oldest first, with their
    session numbers. v1: neighbours may come from adjacent sessions. within=True (v2):
    neighbours only from the same session, so a session's first or last bar can be a
    swing (a gap-down opening bar, say).
    """
    if within:
        return _flip_within(H, L, np.asarray(sess), yday, RH, RL)
    n, k = len(H), SWING_K
    FH = FL = np.nan
    for i in range(n - k - 1, k - 1, -1):
        s = sess[i]
        if s >= yday or s < yday - LOOKBACK:
            continue
        if np.isnan(FH) and H[i] > RH and H[i] > H[i - k:i].max() and H[i] > H[i + 1:i + k + 1].max():
            FH = H[i]
        if np.isnan(FL) and L[i] < RL and L[i] < L[i - k:i].min() and L[i] < L[i + 1:i + k + 1].min():
            FL = L[i]
        if not (np.isnan(FH) or np.isnan(FL)):
            break
    return FH, FL


def _flip_within(H, L, sess, yday, RH, RL):
    k = SWING_K
    FH = FL = np.nan
    for i in range(len(H) - 1, -1, -1):
        s = sess[i]
        if s >= yday:
            continue
        if s < yday - LOOKBACK:
            break
        idx = np.flatnonzero(sess == s)
        a, b = max(idx[0], i - k), min(idx[-1] + 1, i + k + 1)
        nb = np.r_[np.arange(a, i), np.arange(i + 1, b)]
        if np.isnan(FH) and H[i] > RH and (len(nb) == 0 or H[i] > H[nb].max()):
            FH = H[i]
        if np.isnan(FL) and L[i] < RL and (len(nb) == 0 or L[i] < L[nb].min()):
            FL = L[i]
        if not (np.isnan(FH) or np.isnan(FL)):
            break
    return FH, FL


def pattern(O, H, L, C, atr, RH, RL, FH, FL, sp):
    """Candles 1 and 2 -> dict(side, level, trig, stop, tgt) or None. side -1 = short."""
    if len(O) < 2 or not (atr > 0):
        return None
    rng0 = H[0] - L[0]
    if rng0 < sp.strong * atr or abs(C[0] - O[0]) < sp.body * rng0:
        return None
    u = atr if sp.unit == "atr" else rng0                   # the unit every tolerance is in
    against = (lambda d: d < 0) if sp.unit == "atr" else (lambda d: d <= sp.flat * rng0)
    if C[0] > O[0]:                                         # bullish candle 1 -> short at RH / FH
        reach = [(lv, nm) for lv, nm in ((RH, "RH"), (FH, "FH")) if np.isfinite(lv) and H[0] >= lv - sp.tol * u]
        if not reach:
            return None
        lv, nm = max(reach)
        if not (C[0] < lv and against(C[1] - O[1]) and C[1] < lv and H[1] <= max(lv, H[0]) + BRK * u):
            return None
        trig, stop = L[1], max(H[0], H[1]) + STOP_BUF * u
        tgt = {"opp": RL, "near": RH if nm == "FH" else RL, "2R": trig - 2 * (stop - trig)}[sp.target]
        return dict(side=-1, level=nm, trig=trig, stop=stop, tgt=tgt)
    if C[0] < O[0]:                                         # bearish candle 1 -> long at RL / FL
        reach = [(lv, nm) for lv, nm in ((RL, "RL"), (FL, "FL")) if np.isfinite(lv) and L[0] <= lv + sp.tol * u]
        if not reach:
            return None
        lv, nm = min(reach)
        if not (C[0] > lv and against(O[1] - C[1]) and C[1] > lv and L[1] >= min(lv, L[0]) - BRK * u):
            return None
        trig, stop = H[1], min(L[0], L[1]) - STOP_BUF * u
        tgt = {"opp": RH, "near": RL if nm == "FL" else RH, "2R": trig + 2 * (trig - stop)}[sp.target]
        return dict(side=1, level=nm, trig=trig, stop=stop, tgt=tgt)
    return None


def exits(o, h, l, c, j, side, fill, stop, tgt, starts=None, trail=False):
    """Exits from fill bar j onward. -> (R gross, outcome 0 stop / 1 target / 2 close).

    In the fill bar only the stop counts. Later bars: stop first, gaps fill at the open.
    trail=True: break-even at +1R, then the last completed 15-minute high (short) / low (long).
    trail="his": after +1R, the stop follows the extreme of the last three 5-minute bars,
    closer to how he trailed his live trade (v2 Amendment 1).
    """
    risk = side * (fill - stop)
    best = fill
    ends15 = set((starts[1:] - 1).tolist()) if trail is True else ()
    for i in range(j, len(c)):
        if side < 0:
            if h[i] >= stop:
                px = max(stop, o[i]) if i > j else stop
                return side * (px - fill) / risk, 0
            if i > j and l[i] <= tgt:
                return side * (min(tgt, o[i]) - fill) / risk, 1
            best = min(best, l[i])
        else:
            if l[i] <= stop:
                px = min(stop, o[i]) if i > j else stop
                return side * (px - fill) / risk, 0
            if i > j and h[i] >= tgt:
                return side * (max(tgt, o[i]) - fill) / risk, 1
            best = max(best, h[i])
        if trail == "his" and side * (best - fill) >= risk and i >= 2:
            lvl = h[i - 2:i + 1].max() if side < 0 else l[i - 2:i + 1].min()
            stop = min(stop, lvl) if side < 0 else max(stop, lvl)
        elif trail is True and i in ends15 and side * (best - fill) >= risk:
            a = starts[starts <= i][-1]
            lvl = h[a:i + 1].max() if side < 0 else l[a:i + 1].min()
            stop = min(stop, fill, lvl) if side < 0 else max(stop, fill, lvl)
    return side * (c[-1] - fill) / risk, 2


def execute(o, h, l, c, hh, p, win_end=WIN_END, starts=None, trail=False):
    """Work the stop order at p['trig'] from 10:00 to win_end. -> dict or None."""
    side, trig, stop, tgt = p["side"], p["trig"], p["stop"], p["tgt"]
    for j in np.flatnonzero((hh >= 10) & (hh <= win_end + 1e-9)):
        if side < 0:
            if o[j] >= stop:
                return None                                  # opened through the stop: cancelled
            if l[j] <= trig:
                fill = min(trig, o[j])
                break
            if h[j] >= stop:
                return None
        else:
            if o[j] <= stop:
                return None
            if h[j] >= trig:
                fill = max(trig, o[j])
                break
            if l[j] <= stop:
                return None
    else:
        return None
    if side * (tgt - fill) <= 0:
        return None                                          # the target is not beyond the entry
    R, out = exits(o, h, l, c, j, side, fill, stop, tgt, starts, trail)
    return dict(R=R, out=out, j=int(j), fill=fill, risk=side * (fill - stop),
                cost=1e-4 * fill / (side * (fill - stop)), tgt_R=side * (tgt - fill) / (side * (fill - stop)))


def random_entries(o, h, l, c, hh, side, risk, reward, rng, win_end=WIN_END, after=None):
    """N_DRAWS entries at the open of random bars in the window, same distances.

    after (v2): draw only from the real trade's fill bar onward. Drawing earlier bars
    of a day on which the real order filled lets the control know that price later
    reached the trigger, a look-ahead in its favour (v2 Amendment 2)."""
    js = np.flatnonzero((hh >= 10) & (hh <= win_end + 1e-9))
    if after is not None:
        js = js[js >= after]
    R, cost = [], []
    for j in rng.choice(js, size=N_DRAWS, replace=True):
        f = o[j]
        r, _ = exits(o, h, l, c, j, side, f, f - side * risk, f + side * reward)
        R.append(r); cost.append(1e-4 * f / risk)
    return np.mean(R), np.mean(cost)


def levels_from(hist, within=False):
    """RH, RL, FH, FL known at today's open, from the stored prior sessions."""
    y = hist[-1]
    H = np.concatenate([s["H15"] for s in hist]); L = np.concatenate([s["L15"] for s in hist])
    sess = np.concatenate([np.full(len(s["H15"]), k) for k, s in enumerate(hist)])
    FH, FL = flip_levels(H, L, sess, len(hist) - 1, y["hi"], y["lo"], within)
    return y["hi"], y["lo"], FH, FL


def name_day(o, h, l, c, hh, hist, rng, version=1):
    """One name, one day. hist: prior sessions, oldest first, each with H15, L15, hi, lo,
    open, ratios (its own levels / its 09:30 open). Returns (rows, today's session record).
    version 2 uses within-session flip swings and the candle-1-unit grid."""
    grid, primary, within = (GRID, PRIMARY, False) if version == 1 else (GRID_V2, PRIMARY_V2, True)
    O, H, L, C, starts = bars15(o, h, l, c, hh)
    today = dict(H15=H, L15=L, hi=h.max(), lo=l.min(), open=o[0], ratios=None)
    if len(hist) < 2 or len(O) < 6:
        return [], today
    ranges = np.concatenate([hist[-1]["H15"] - hist[-1]["L15"]])[-ATR_N:]
    atr = ranges.mean() if len(ranges) == ATR_N else np.nan
    lv = levels_from(hist, within)
    today["ratios"] = np.array(lv) / o[0]
    pool = [s for s in hist[-(LOOKBACK + 1):-1] if s["ratios"] is not None]
    fake = tuple(rng.choice(pool)["ratios"] * o[0]) if pool else None
    rows = []
    for kind, levels in (("real", lv), ("fake", fake)):
        if levels is None or not np.isfinite(atr):
            continue
        for sp in grid:
            p = pattern(O, H, L, C, atr, *levels, sp)
            if p is None:
                continue
            ex = execute(o, h, l, c, hh, p)
            if ex is None:
                continue
            row = dict(kind=kind, strong=sp.strong, body=sp.body, tol=sp.tol, target=sp.target, flat=sp.flat,
                       side=p["side"], level=p["level"], atr=atr, fill_t=hh[ex["j"]],
                       trig=p["trig"], stop=p["stop"], tgt=p["tgt"], **ex)
            if kind == "real":
                row["R_rand"], row["c_rand"] = random_entries(o, h, l, c, hh, p["side"], ex["risk"],
                                                              ex["tgt_R"] * ex["risk"], rng,
                                                              after=ex["j"] if version == 2 else None)
                if sp == primary:
                    late = execute(o, h, l, c, hh, p, WIN_END_LATE)
                    tr = execute(o, h, l, c, hh, p, starts=starts, trail=True)
                    tr2 = execute(o, h, l, c, hh, p, starts=starts, trail="his")
                    row["R_late"], row["c_late"] = (late["R"], late["cost"]) if late else (np.nan, np.nan)
                    row["R_trail"] = tr["R"] if tr else np.nan
                    row["R_trail_his"] = tr2["R"] if tr2 else np.nan
            rows.append(row)
    return rows, today
