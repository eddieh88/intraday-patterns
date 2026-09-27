"""The zone trade with the stop refined after confirmation -- the only way his
published process yields both his entry and his 1:3+ (see NOTES.md). Rules and the
random control are fixed in prereg/fut_zone_refined.md before this was first run.

  setups  : structure.py (1-hour break of structure, zone at the impulse base)
  filters : 4-hour trend agrees; zone >= 0.3 x 30-min ATR; not an FOMC/payrolls
            impulse; setup expires on a trend flip, after 5 days or Friday 17:00
  trigger : after price reaches the zone, a 5-minute close beyond the latest 5-minute
            swing formed since the touch (structure_fair.trigger); entry at that close
  stop    : 1 tick beyond the pullback's extreme between touch and trigger, but never
            closer than 1 x the 5-minute ATR(14) at entry (the floor widens it)
  target  : the impulse extreme; planned reward:risk at entry must be >= 3
  exit    : stop, target or 10 days. Costs 2 ticks round trip + 1 tick slippage on stops
  control : per trade, 20 random 5-minute bars, same market, same hour of day, same
            direction with the 4-hour trend agreeing; stop and target the same
            distances in 5-minute ATRs; same exits and costs

  python3 explore_fut/structure_refined.py [dev|holdout]
"""
import pandas as pd, numpy as np, sys, time
from structure import load, bars, structure, zone, TICK, t0
from structure_fair import trend_at, news_times, friday_close, atr, trigger

N_CTRL, SEED, FLOOR = 20, 7, 1.0

def sim(H, L, C, ts, i, side, entry, stop, target, tk):
    """exit from bar i+1 on: stop first within a bar, then target, else close at 10 days -> (R, how)"""
    j = np.searchsorted(ts, ts[i] + np.timedelta64(10, "D"), side="right")
    h, l = H[i + 1:j], L[i + 1:j]
    if len(h) == 0: return np.nan, "none"
    hs = (l <= stop) if side > 0 else (h >= stop)
    ht = (h >= target) if side > 0 else (l <= target)
    a = hs.argmax() if hs.any() else 10**9; b = ht.argmax() if ht.any() else 10**9
    R = (entry - stop) * side
    if a <= b and a < 10**9: px, how, cost = stop, "stop", 3 * tk
    elif b < 10**9: px, how, cost = target, "target", 2 * tk
    else: px, how, cost = C[j - 1], "time", 2 * tk
    return ((px - entry) * side - cost) / R, how

def main(period):
    data = load(period); news = news_times(); rng = np.random.default_rng(SEED); rows, ctrl = [], []
    for s, m5 in data.items():
        tk = TICK[s]; h1, m30, h4 = bars(m5, "1h"), bars(m5, "30min"), bars(m5, "4h")
        tr4, a30, a5 = trend_at(h4), atr(m30), atr(m5)
        H, L, C, ts = m5.high.values, m5.low.values, m5.close.values, m5.index.values
        tr5 = tr4.reindex(m5.index, method="ffill").fillna(0).values      # 4h trend in force at each 5m bar
        A5 = a5.values; hr = m5.index.hour.values
        last_ok = np.searchsorted(ts, ts[-1] - np.timedelta64(10, "D"))
        ev = structure(h1); idx1 = h1.index; flips = [(e[0], e[1]) for e in ev]
        for k, (j, side, lvl, p, prot) in enumerate(ev):
            z = zone(m30, idx1[p], idx1[j] + pd.Timedelta("59min"), side)
            if z is None: continue
            zt, (near, far) = z; bos_close = idx1[j] + pd.Timedelta("1h")
            t4 = tr4[tr4.index <= bos_close]
            if not (len(t4) and t4.iloc[-1] == side): continue
            w = a30.loc[:zt].dropna()
            if not (len(w) and abs(near - far) >= 0.3 * w.iloc[-1]): continue
            if ((idx1[p] - pd.Timedelta("30min") <= news) & (news <= idx1[p] + pd.Timedelta("90min"))).any(): continue
            nxt = [f for f in flips[k + 1:] if f[1] != side]
            valid_to = min(idx1[nxt[0][0]] if nxt else idx1[-1], idx1[j] + pd.Timedelta("5D"), friday_close(bos_close))
            after = m5.loc[bos_close:valid_to]
            touch = after.low <= near if side > 0 else after.high >= near
            if not touch.any(): continue
            tt = touch.idxmax(); big_stop = far - tk if side > 0 else far + tk
            trg = trigger(after.loc[tt:], side, big_stop)
            if trg is None: continue
            ft, entry = trg; i = m5.index.get_loc(ft)
            if i >= last_ok or np.isnan(A5[i]): continue
            pb = m5.loc[tt:ft]
            stop = pb.low.min() - tk if side > 0 else pb.high.max() + tk
            floored = (entry - stop) * side < FLOOR * A5[i]
            if floored: stop = entry - side * FLOOR * A5[i]
            target = (m5.loc[idx1[p]:ft].high.max() if side > 0 else m5.loc[idx1[p]:ft].low.min())
            Rd = (entry - stop) * side; rr = (target - entry) * side / Rd
            if rr < 3: continue
            R, how = sim(H, L, C, ts, i, side, entry, stop, target, tk)
            rows.append(dict(sym=s, side=side, bos=idx1[j], fill_t=ft, entry=entry, stop=stop, target=target, rr=rr,
                             R_ticks=Rd / tk, floored=floored, stop_atr=Rd / A5[i], how=how, R=R))
            # control: same market, hour, direction, 4h trend agreeing; same stop/target in 5m ATRs
            cand = np.flatnonzero((hr == hr[i]) & (tr5 == side) & ~np.isnan(A5) & (np.arange(len(ts)) < last_ok))
            for c in rng.choice(cand, size=min(N_CTRL, len(cand)), replace=False):
                e = C[c]; sd = Rd / A5[i] * A5[c]
                r_, h_ = sim(H, L, C, ts, c, side, e, e - side * sd, e + side * rr * sd, tk)
                ctrl.append(dict(sym=s, side=side, fill_t=pd.Timestamp(ts[c]), rr=rr, R_ticks=sd / tk, how=h_, R=r_, of=ft))
        print(f"  {s}: {sum(1 for x in rows if x['sym']==s)} trades  ({time.time()-t0:.0f}s)", flush=True)
    suf = "" if period == "dev" else "_holdout"
    pd.DataFrame(rows).to_parquet(f"cache/fut_zone_refined{suf}.parquet", index=False)
    pd.DataFrame(ctrl).to_parquet(f"cache/fut_zone_refined_ctrl{suf}.parquet", index=False)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
