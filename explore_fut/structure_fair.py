"""The zone trade with the filters a practitioner review said structure.py left out.
Rules fixed before any outcome was looked at. Development only (to 2025-03-31).

  F1 trend    : the 4-hour structure (same break-of-structure logic on 4h bars, only
                closed bars) must point the same way as the 1-hour break
  F3 trigger  : no resting limit. Once price reaches the zone, wait for a 5-minute
                CLOSE beyond the latest 5-minute swing formed since the touch (a
                lower-timeframe break in the trade's direction); enter at that close.
                A trade through the stop first cancels the setup
  F4 width    : zone at least 0.3 x the 30-minute ATR(14) -- a tighter box is noise
  F5 news     : skip impulses whose origin bar is within 30 minutes of an FOMC
                decision (14:00) or payrolls (08:30, first Friday). CPI and foreign
                central banks are NOT covered -- no calendar on hand
  F6 3:1      : planned reward:risk at entry at least 3
  F7 weekend  : setups expire Friday 17:00 New York

  Not implemented: "cancel on an opposite 1-hour break before the tap". The zone sits
  at the impulse's origin, so reaching it means retracing through every internal swing
  of the impulse; on 1-hour closes that rule cancels nearly every setup by
  construction. The trend flip (close beyond the protected level) still cancels, as
  in structure.py, and F3 + F7 cover the two cases it was aimed at.

  python3 explore_fut/structure_fair.py   -> cache/fut_zone_fair.parquet
"""
import pandas as pd, numpy as np, time
from structure import load, bars, structure, zone, context, TICK, t0

def trend_at(h4):
    """4-hour trend in force after each 4h bar closes -> Series indexed by close time"""
    ev = structure(h4); tr = np.zeros(len(h4))
    for j, side, *_ in ev: tr[j:] = side
    return pd.Series(tr, index=h4.index + pd.Timedelta("4h"))

def news_times():
    f = pd.read_csv("data/calendar/fomc_decisions.csv", parse_dates=["date"])
    t = list(f.date + pd.Timedelta("14h"))
    for m in pd.date_range("2021-01-01", "2025-04-01", freq="MS"):
        fri = m + pd.Timedelta(days=(4 - m.weekday()) % 7); t.append(fri + pd.Timedelta("8h30min"))
    return pd.DatetimeIndex(sorted(t))

def friday_close(t):
    d = t.normalize() + pd.Timedelta(days=(4 - t.weekday()) % 7) + pd.Timedelta("17h")
    return d if d > t else d + pd.Timedelta("7D")

def atr(m30, n=14):
    pc = m30.close.shift()
    tr = pd.concat([m30.high - m30.low, (m30.high - pc).abs(), (m30.low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def trigger(seg, side, stop):
    """first 5-minute close beyond the latest swing (2 bars each side) formed since the
    touch -> (time, price) or None; None also if the stop trades first"""
    H, L, C, ix = seg.high.values, seg.low.values, seg.close.values, seg.index
    lvl = None
    for i in range(len(C)):
        if (L[i] <= stop) if side > 0 else (H[i] >= stop): return None
        k = i - 2                                               # swing at k is known at i
        if k >= 2:
            if side > 0 and H[k] > H[k-2:k].max() and H[k] >= H[k+1:k+3].max(): lvl = H[k]
            if side < 0 and L[k] < L[k-2:k].min() and L[k] <= L[k+1:k+3].min(): lvl = L[k]
        if lvl is not None and (C[i] > lvl if side > 0 else C[i] < lvl): return ix[i], C[i]
    return None

def main():
    data = load(); news = news_times(); rows = []
    for s, m5 in data.items():
        tk = TICK[s]; h1, m30, h4 = bars(m5, "1h"), bars(m5, "30min"), bars(m5, "4h")
        tr4, a30 = trend_at(h4), atr(m30)
        ev = structure(h1); idx1 = h1.index; flips = [(e[0], e[1]) for e in ev]
        for k, (j, side, lvl, p, prot) in enumerate(ev):
            z = zone(m30, idx1[p], idx1[j] + pd.Timedelta("59min"), side)
            if z is None: continue
            zt, (near, far) = z; bos_close = idx1[j] + pd.Timedelta("1h")
            r = dict(sym=s, bos=idx1[j], side=side, zone_t=zt, near=near, far=far, origin=idx1[p])
            t4 = tr4[tr4.index <= bos_close]
            r["f_trend"] = bool(len(t4) and t4.iloc[-1] == side)
            w = a30.loc[:zt].dropna(); r["f_width"] = bool(len(w) and abs(near - far) >= 0.3 * w.iloc[-1])
            r["f_news"] = bool(not ((idx1[p] - pd.Timedelta("30min") <= news) & (news <= idx1[p] + pd.Timedelta("90min"))).any())
            nxt = [f for f in flips[k + 1:] if f[1] != side]
            valid_to = min(idx1[nxt[0][0]] if nxt else idx1[-1], idx1[j] + pd.Timedelta("5D"), friday_close(bos_close))
            after = m5.loc[bos_close:valid_to]
            touch = after.low <= near if side > 0 else after.high >= near
            if not touch.any(): rows.append({**r, "filled": False}); continue
            tt = touch.idxmax(); stop = far - tk if side > 0 else far + tk
            trg = trigger(after.loc[tt:], side, stop)
            if trg is None: rows.append({**r, "filled": False, "touched": True}); continue
            ft, entry = trg; R = (entry - stop) * side
            ext = m5.loc[idx1[p]:ft]; target = ext.high.max() if side > 0 else ext.low.min()
            rr = (target - entry) * side / R
            if rr <= 0: rows.append({**r, "filled": False, "touched": True}); continue
            path = m5.loc[ft:ft + pd.Timedelta("10D")].iloc[1:]         # entry is at the trigger bar's close
            px, how, xt = path.close.iloc[-1], "time", path.index[-1]
            for t_, b in path.iterrows():
                if (b.low <= stop) if side > 0 else (b.high >= stop):
                    px, how, xt = (min(stop, b.open) if side > 0 else max(stop, b.open)), "stop", t_; break
                if (b.high >= target) if side > 0 else (b.low <= target):
                    px, how, xt = target, "target", t_; break
            swept, cheap = context(h1, j, p, side)
            rows.append({**r, "filled": True, "touched": True, "fill_t": ft, "entry": entry, "stop": stop, "target": target,
                         "R_ticks": R / tk, "rr": rr, "f_rr": rr >= 3, "exit_t": xt, "how": how, "swept": swept, "cheap": cheap,
                         "R": ((px - entry) * side - 2 * tk) / R})
        print(f"  {s}: {sum(1 for x in rows if x['sym']==s and x['filled'])} triggered  ({time.time()-t0:.0f}s)", flush=True)
    T = pd.DataFrame(rows); T.to_parquet("cache/fut_zone_fair.parquet", index=False)

if __name__ == "__main__":
    main()
