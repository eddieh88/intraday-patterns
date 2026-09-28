"""5-minute setups, explored before any results are looked at. Development only.

Universe: each day's point-in-time top 100 (cache/intraday_pool.parquet).
Bars are stamped at their start; regular hours 09:30 to the close (13:00 on a
detected early close). Every trade is flat by the close.

  tension base (long; short is the mirror)
    base      = the 18 bars (90 minutes) before the signal bar
    ceiling   : the base high was set in its first 9 bars, and a high in its last
                6 bars came within 0.25 ATR of it
    sideways  : |close at base end - close at base start| <= 50% of the base range
    tightening: range of the last 6 bars <= 60% of the base range
    quiet     : mean volume of the last 6 bars < mean volume of the first 12
    signal    : first close above the base high (first per name, day and side)
  turtle soup (long; short is the mirror), after the MarkitTick / Connors-Raschke rules
    channel   = the lowest low of the prior 20 bars, set at least 4 bars ago
    signal    : the bar trades below the channel low and closes back above it
                (first per name, day and side)

  ATR = mean high-low of the prior 14 bars.
  stop: base setups -> under the most recent swing low (a low beneath the 3 bars
        either side); turtle soup -> 0.25 ATR beyond the signal bar's extreme.
  entry: next bar's open. Target +3R. Otherwise the close.

  coil (long; short is the mirror) -- stricter tension, with a real breakout
    base      : the 12 bars (60 minutes) before the signal bar
    narrow    : the base spans at most 3 ATR
    pressing  : >= 2 separate pushes to within 0.15 ATR of the high, the first in
                the base's first half, the last in its final 3 bars; the last 4
                closes all in the top 40% of the range
    rising    : each third of the base has a higher low than the one before
    quiet     : base volume < 0.9x normal for those time slots (prior 20 sessions)
    breakout  : first close above the high, on >= 1.5x normal volume for the slot
    stop      : under the low of the last 4 bars; 1R >= 0.3% of price

  python3 explore5m/detect.py [every_nth_session]   -> cache/x5_events.parquet
"""
import pandas as pd, numpy as np, glob, sys, time
from paths import add_to_path
add_to_path("selection")
from intraday_levels import session_frames
from holdout import HOLDOUT_START, assert_sealed
from session_summary import session_close

STEP = int(sys.argv[1]) if len(sys.argv) > 1 else 1
NB, LATE, CH, AGE = 18, 6, 20, 4
CNB, CLATE, PUSHES, VOLX = 12, 4, 2, 1.5      # coil: 60-min base, 2 pushes, 1.5x slot volume

def swing(x, t, k=3, low=True, lookback=40):
    for i in range(t - k, max(k, t - lookback) - 1, -1):
        w = x[i - k:i + k + 1]
        if (low and x[i] <= w.min()) or (not low and x[i] >= w.max()): return i
    return None

def trade(o, h, l, c, t, side, stop):
    """entry next open; stop intraday (first on a tie); +3R; else the last close."""
    if t + 2 >= len(c): return None
    e = o[t + 1]; R = (e - stop) * side
    if not (R > 0): return None
    tgt = e + 3 * R * side
    for j in range(t + 1, len(c)):
        if (l[j] <= stop) if side > 0 else (h[j] >= stop):
            px = min(stop, o[j]) if side > 0 else max(stop, o[j]); return e, stop, R, j, px, "stop"
        if (h[j] >= tgt) if side > 0 else (l[j] <= tgt):
            px = max(tgt, o[j]) if side > 0 else min(tgt, o[j]); return e, stop, R, j, px, "target"
    return e, stop, R, len(c) - 1, c[-1], "close"

def coil(o, h, l, c, v, nv, atr, t, side):
    """A coil under a flat ceiling (long) or over a flat floor (short), then a real breakout.
    nv = normal volume for each bar's time slot (prior 20 sessions)."""
    hw, lw, cw = h[t-CNB:t], l[t-CNB:t], c[t-CNB:t]
    if side < 0: hw, lw, cw = -lw, -hw, -cw                      # mirror: a floor becomes a ceiling
    top, bot = hw.max(), lw.min(); rng = top - bot; a = atr[t]
    if not (rng > 0 and rng <= 3 * a): return None                # narrow for this stock, right now
    near = hw >= top - .15 * a                                     # bars pressing the ceiling
    pushes = np.flatnonzero(near & ~np.r_[False, near[:-1]])       # starts of separate pushes
    if len(pushes) < PUSHES or pushes[0] >= CNB // 2 or np.flatnonzero(near)[-1] < CNB - 3: return None
    thirds = [lw[i:i + CNB // 3].min() for i in range(0, CNB, CNB // 3)]
    if not (thirds[0] < thirds[1] < thirds[2]): return None       # rising lows
    if not (cw[-CLATE:] >= bot + .6 * rng).all(): return None     # pressing at the end
    base_vol = v[t-CNB:t].sum() / np.nansum(nv[t-CNB:t])
    if not (base_vol < .9): return None                           # quiet for the time of day
    ct, cp = (c[t], c[t-1]) if side > 0 else (-c[t], -c[t-1])
    if not (ct > top and cp <= top): return None                  # first close through
    volx = v[t] / nv[t]
    if not (np.isfinite(volx) and volx >= VOLX): return None      # a real breakout, for the time of day
    stop = (l[t-CLATE:t].min() * .9995) if side > 0 else (h[t-CLATE:t].max() * 1.0005)
    return stop, (top if side > 0 else -top), (bot if side > 0 else -bot), base_vol, volx

def detect(g, nv=None):
    o, h, l, c, v = (g[k].values.astype(float) for k in ("open","high","low","close","volume"))
    n = len(c); atr = pd.Series(h - l).rolling(14, min_periods=10).mean().shift(1).values
    out, seen = [], set()
    for t in range(max(NB, CH) + 1, n - 2):
        if not np.isfinite(atr[t]) or atr[t] <= 0: continue
        for side in (1, -1):
            # coil (only when the time-of-day volume baseline is available)
            if nv is not None and ("coil", side) not in seen:
                z = coil(o, h, l, c, v, nv, atr, t, side)
                if z:
                    stop, lv1, lv2, bv, vx = z
                    r = trade(o, h, l, c, t, side, stop)
                    if r and r[2] / r[0] >= .003:                 # 1R at least 0.3% of price
                        a_i = t - CLATE + int(np.argmin(l[t-CLATE:t]) if side > 0 else np.argmax(h[t-CLATE:t]))
                        out.append(("coil", side, t, a_i, lv1, lv2, *r, bv, vx)); seen.add(("coil", side))
            # tension base
            if ("base", side) not in seen:
                hw, lw, cw, vw = h[t-NB:t], l[t-NB:t], c[t-NB:t], v[t-NB:t]
                top, bot = hw.max(), lw.min(); rng = top - bot
                if rng > 0:
                    edge = hw if side > 0 else -lw; lvl = top if side > 0 else bot
                    ok = (int(np.argmax(edge)) < NB // 2 and edge[-LATE:].max() >= edge.max() - .25 * atr[t]
                          and abs(cw[-1] - cw[0]) <= .5 * rng
                          and (hw[-LATE:].max() - lw[-LATE:].min()) <= .6 * rng
                          and vw[-LATE:].mean() < vw[:NB - LATE].mean()
                          and ((c[t] > lvl and c[t-1] <= lvl) if side > 0 else (c[t] < lvl and c[t-1] >= lvl)))
                    if ok:
                        a = swing(l if side > 0 else h, t, low=side > 0)
                        if a is not None:
                            stop = l[a] * .9995 if side > 0 else h[a] * 1.0005
                            r = trade(o, h, l, c, t, side, stop)
                            if r: out.append(("base", side, t, a, top, bot, *r, np.nan, np.nan)); seen.add(("base", side))
            # turtle soup
            if ("soup", side) not in seen:
                seg = l[t-CH:t] if side > 0 else h[t-CH:t]
                i_ext = int(np.argmin(seg)) if side > 0 else int(np.argmax(seg))
                ext = seg[i_ext]; age = CH - i_ext
                hit = (l[t] < ext and c[t] > ext) if side > 0 else (h[t] > ext and c[t] < ext)
                if age >= AGE and hit:
                    stop = l[t] - .25 * atr[t] if side > 0 else h[t] + .25 * atr[t]
                    r = trade(o, h, l, c, t, side, stop)
                    if r: out.append(("soup", side, t, t - CH + i_ext, ext, np.nan, *r, np.nan, np.nan)); seen.add(("soup", side))
    return out

def main():
    pool = pd.read_parquet("cache/intraday_pool.parquet"); pool = pool[(pool.rk <= 100) & (pool.date < HOLDOUT_START)]
    by_day = pool.groupby("date").symbol.apply(set)
    files = [f for f in sorted(glob.glob("cache/mp5min/*.parquet")) if pd.Timestamp(f.split("_")[-1][:10]) in by_day.index][::STEP]
    SV = pd.read_parquet("cache/x5_slotvol.parquet"); SV["symbol"] = SV.symbol.astype(str)
    SV = {d: g.set_index(["symbol","slot"]).slot_norm for d, g in SV.groupby("date")}
    rows, t0 = [], time.time()
    for k, f in enumerate(files):
        day = pd.Timestamp(f.split("_")[-1][:10])
        full = pd.read_parquet(f, columns=["timestamp","symbol","volume"]).dropna(subset=["symbol"])
        close_h = session_close(full)
        for sym, d, g in session_frames([f], by_day[day]):
            g = g[(g.h >= 9.5) & (g.h < close_h)].reset_index(drop=True)
            if len(g) < 40: continue
            sv = SV.get(day)
            nv = None
            if sv is not None:
                slots = (g.ts.dt.hour * 60 + g.ts.dt.minute).values
                nv = np.array([sv.get((sym, s_), np.nan) for s_ in slots], dtype=float)
            for (kind, side, t, anchor, lvl, lvl2, e, stop, R, j, px, how, bv, vx) in detect(g, nv):
                rows.append(dict(date=day, symbol=sym, kind=kind, side=side, t=t, anchor=anchor, level=lvl, level2=lvl2,
                                 entry=e, stop=stop, R_pct=R / e, exit_bar=j, exit=px, how=how, R=(px - e) * side / R,
                                 bar_time=g.ts.iloc[t].strftime("%H:%M"), base_vol=bv, brk_volx=vx))
        if k % 50 == 0: print(f"  {k}/{len(files)}  {day.date()}  {len(rows):,}  {time.time()-t0:.0f}s", flush=True)
    E = pd.DataFrame(rows); assert_sealed(E.date)
    E.to_parquet("cache/x5_events.parquet", index=False)
    print(f"{len(E):,} signals over {E.date.nunique()} sessions  ({time.time()-t0:.0f}s)")
    print(E.groupby(["kind","side"]).size().rename("signals").to_string())

if __name__ == "__main__":
    main()
