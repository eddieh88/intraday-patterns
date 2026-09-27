"""Market structure + supply/demand zones on gold and currency futures, after the
rules in the three videos. Development only (to 2025-03-31). Timestamps are New
York time (the missing hour is the 17:00 CME break).

  swings   : 1-hour fractals (a high above the 2 bars either side; mirror for lows),
             usable only once the 2 bars after them have closed -- no look-ahead
  BOS      : a 1-hour CLOSE beyond the latest confirmed swing. Wicks never count.
             In an uptrend only a close below the protected low (the low that
             launched the last bullish impulse) flips the trend; smaller breaks are
             internal structure and ignored. Mirror for downtrends.
  zone     : the BASE of the impulse on 30-minute bars -- the candle at its swing
             extreme plus the one before, boxed from the extreme to the top of their
             bodies; valid if the move away left a 3-candle imbalance and price has
             not come back into the box by the break
  trade    : limit at the box's near edge, filled on EVERY touch (5-minute bars),
             stop 1 tick beyond the swing extreme, target the impulse extreme at
             fill time; valid until the trend flips or 5 days pass; 10-day limit
  cost     : 2 ticks round trip

  python3 explore_fut/structure.py            -> cache/fut_zone_trades.parquet
  python3 explore_fut/structure.py holdout    -> cache/fut_zone_trades_holdout.parquet (sealed)
"""
import pandas as pd, numpy as np, glob, sys, time, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib.holdout import assert_sealed
t0 = time.time()
DEV_END = pd.Timestamp("2025-04-01")
TICK = {"GC": 0.1, "E6": 0.00005, "B6": 0.0001, "A6": 0.00005, "J1": 0.0000005}
SYMS = list(TICK)

def load(period="dev"):
    """dev: before 2025-04-01. holdout: from 2025-04-01, sealed unless HOLDOUT_UNLOCK=final-evaluation"""
    rows = []
    for f in sorted(glob.glob("cache/mp_futures_5min/*.parquet")):
        if (pd.Timestamp(f.split("_")[-1][:10]) >= DEV_END) != (period == "holdout"): continue
        d = pd.read_parquet(f); rows.append(d[d.symbol.isin(SYMS)])
    D = pd.concat(rows); D["ts"] = pd.to_datetime(D.timestamp)
    if period == "holdout": assert_sealed(D.ts)
    return {s: g.sort_values("ts").set_index("ts")[["open","high","low","close","volume"]] for s, g in D.groupby("symbol")}

def bars(df, rule):
    return df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna(subset=["open"])

def structure(h1):
    """-> list of BOS events: (bar index, side, broken level, impulse origin index, new protected level)"""
    H, L, C = h1.high.values, h1.low.values, h1.close.values; n = len(C)
    sh = [i for i in range(2, n - 2) if H[i] > H[i-2:i].max() and H[i] >= H[i+1:i+3].max()]
    sl = [i for i in range(2, n - 2) if L[i] < L[i-2:i].min() and L[i] <= L[i+1:i+3].min()]
    shc = {i + 2: i for i in sh}; slc = {i + 2: i for i in sl}      # a swing is known only 2 bars later
    last_sh = last_sl = None; used_h, used_l = set(), set()
    trend, prot, prot_i, ev = 0, None, None, []
    for j in range(n):
        if j in shc: last_sh = shc[j]
        if j in slc: last_sl = slc[j]
        # bullish break: in a downtrend only the protected high counts; otherwise the latest unbroken swing high
        if trend == -1: lvl, ref = prot, prot_i
        elif last_sh is not None and last_sh not in used_h: lvl, ref = H[last_sh], last_sh
        else: lvl = None
        if lvl is not None and C[j] > lvl:
            p = ref + int(np.argmin(L[ref:j + 1]))                    # the low that launched the impulse
            ev.append((j, 1, lvl, p, L[p])); trend, prot, prot_i = 1, L[p], p
            if last_sh is not None: used_h.add(last_sh)
            continue
        if trend == 1: lvl, ref = prot, prot_i
        elif last_sl is not None and last_sl not in used_l: lvl, ref = L[last_sl], last_sl
        else: lvl = None
        if lvl is not None and C[j] < lvl:
            p = ref + int(np.argmax(H[ref:j + 1]))
            ev.append((j, -1, lvl, p, H[p])); trend, prot, prot_i = -1, H[p], p
            if last_sl is not None: used_l.add(last_sl)
    return ev

def zone(m30, t_from, t_to, side):
    """The BASE of the impulse, as in his charts: the 30-minute candle at the impulse's
    extreme (the swing low for a long) plus the candle before it. Box = from that
    extreme to the top of those candles' bodies. Valid only if the move away left a
    3-candle imbalance within the next 3 candles and price has not come back into the
    box by the break. -> (base time, (near edge, far edge)) or None"""
    w = m30.loc[t_from:t_to]
    if len(w) < 4: return None
    o, h, l, c = w.open.values, w.high.values, w.low.values, w.close.values
    k = int(np.argmin(l)) if side > 0 else int(np.argmax(h))            # the swing extreme
    if k + 3 >= len(w): return None
    base = [x for x in (k - 1, k) if x >= 0]
    if side > 0:
        near, far = max(max(o[x], c[x]) for x in base), l[k]
        gap = any(l[x + 2] > h[x] for x in range(k, min(k + 3, len(w) - 2)))
        clean = l[k + 2:].min() > near
    else:
        near, far = min(min(o[x], c[x]) for x in base), h[k]
        gap = any(h[x + 2] < l[x] for x in range(k, min(k + 3, len(w) - 2)))
        clean = h[k + 2:].max() < near
    if not (gap and clean and (near - far) * side > 0): return None
    return w.index[base[0]], (near, far)

def context(h1, j, p, side):
    """his context marks, recorded for later splits (not filters yet):
    swept  -- the impulse origin took out the prior 48 hours' extreme and closed back inside
    cheap  -- the origin sits in the discount half (long) / premium half (short) of the prior 5 days' range"""
    H, L, C = h1.high.values, h1.low.values, h1.close.values
    lo48, hi48 = L[max(0, p - 48):p].min() if p > 0 else np.nan, H[max(0, p - 48):p].max() if p > 0 else np.nan
    swept = (L[p] < lo48 and C[p] > lo48) if side > 0 else (H[p] > hi48 and C[p] < hi48)
    r_lo, r_hi = L[max(0, p - 120):p + 1].min(), H[max(0, p - 120):p + 1].max()
    mid = (r_lo + r_hi) / 2
    cheap = (L[p] < mid) if side > 0 else (H[p] > mid)
    return bool(swept), bool(cheap)

def main(period="dev"):
    data = load(period); print(f"loaded {len(data)} symbols  ({time.time()-t0:.0f}s)", flush=True)
    rows = []
    for s, m5 in data.items():
        tk = TICK[s]; h1, m30 = bars(m5, "1h"), bars(m5, "30min")
        ev = structure(h1)
        C1, idx1 = h1.close.values, h1.index
        flips = [(e[0], e[1]) for e in ev]
        for k, (j, side, lvl, p, prot) in enumerate(ev):
            z = zone(m30, idx1[p], idx1[j] + pd.Timedelta("59min"), side)
            if z is None: continue
            zt, (near, far) = z
            nxt = [f for f in flips[k + 1:] if f[1] != side]
            valid_to = min(idx1[nxt[0][0]] if nxt else idx1[-1], idx1[j] + pd.Timedelta("5D"))
            after = m5.loc[idx1[j] + pd.Timedelta("1h"):valid_to]
            touch = after.low <= near if side > 0 else after.high >= near
            if not touch.any(): rows.append(dict(sym=s, bos=idx1[j], side=side, filled=False)); continue
            ft = touch.idxmax(); fo = after.loc[ft, "open"]
            entry = min(near, fo) if side > 0 else max(near, fo)
            stop = far - tk if side > 0 else far + tk                  # beyond the swing extreme itself
            R = (entry - stop) * side
            ext = m5.loc[idx1[p]:ft]; target = ext.high.max() if side > 0 else ext.low.min()
            path = m5.loc[ft:ft + pd.Timedelta("10D")]
            px, how, xt = path.close.iloc[-1], "time", path.index[-1]
            for t_, b in path.iterrows():
                if (b.low <= stop) if side > 0 else (b.high >= stop):
                    px, how, xt = (min(stop, b.open) if side > 0 else max(stop, b.open)), "stop", t_; break
                if t_ > ft and ((b.high >= target) if side > 0 else (b.low <= target)):
                    px, how, xt = target, "target", t_; break
            swept, cheap = context(h1, j, p, side)
            rows.append(dict(sym=s, bos=idx1[j], side=side, filled=True, zone_t=zt, near=near, far=far, fill_t=ft, swept=swept, cheap=cheap,
                             entry=entry, stop=stop, target=target, R_ticks=R / tk, rr=(target - entry) * side / R,
                             exit_t=xt, how=how, R=((px - entry) * side - 2 * tk) / R, origin=idx1[p], protected=prot, level=lvl))
        print(f"  {s}: {len(ev)} breaks of structure, {sum(1 for r in rows if r['sym']==s and r['filled'])} zone fills  ({time.time()-t0:.0f}s)", flush=True)
    T = pd.DataFrame(rows); T.to_parquet("cache/fut_zone_trades.parquet" if period == "dev" else "cache/fut_zone_trades_holdout.parquet", index=False)
    F = T[T.filled]
    print(f"\n{len(T):,} zones set up, {len(F):,} filled ({len(F)/len(T):.0%})")
    print(f"planned reward:risk at fill: median {F.rr.median():.1f}, share >= 3: {(F.rr >= 3).mean():.0%};  median 1R = {F.R_ticks.median():.0f} ticks")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
