"""Stage A of prereg/selection.md: one row per (session, symbol), development only.

Every column is one of two kinds, and the audit holds them to it:

  AT0945  known by the close of the 09:40 bar -- usable on the same day
  EOD     end of day -- usable ONLY lagged, as history for later sessions

Bars are stamped at their START (verified: regular hours are 09:30..15:55, 78
bars). "The window" is the 09:30, 09:35 and 09:40 bars. Pre-market is every bar
stamped before 09:30.

  python3 selection/session_summary.py   -> cache/sel_stocks.parquet, cache/sel_etfs.parquet
"""
import pandas as pd, numpy as np, glob, sys, time
from holdout import HOLDOUT_START, assert_sealed

ETFS = ["SPY","XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLU","XLB","XLRE","XLC","SMH","VIXY"]
AT0945 = ["o930","c940","h15","l15","v15","r1","pre_hi","pre_lo","pre_dv"]
EOD = ["rth_o","rth_hi","rth_lo","rth_c"]
COLS = ["timestamp","symbol","open","high","low","close","volume"]
HALF_DAY_SHARE = 0.2

def session_close(bars):
    """13.0 on an early-close day, else 16.0. Extended-hours trading continues after a
    13:00 close, so a fixed 09:30-16:00 filter would count after-hours prints as the
    session. Early closes are detected, not listed: across all names, the share of
    09:30-16:00 volume traded after 13:00 is <= 0.13 on every half day in 2021-26 and
    >= 0.34 on every full day. The close time is on the exchange calendar in advance,
    and only EOD fields depend on it."""
    t = pd.to_datetime(bars.timestamp); h = t.dt.hour + t.dt.minute/60
    share = bars.volume[(h >= 13) & (h < 16)].sum() / bars.volume[(h >= 9.5) & (h < 16)].sum()
    return 13.0 if share < HALF_DAY_SHARE else 16.0

def summarise(bars, close_h=16.0):
    """bars: one session's 5-minute bars, any number of symbols -> one row per symbol."""
    t = pd.to_datetime(bars.timestamp)
    b = bars.assign(h=(t.dt.hour + t.dt.minute/60).values, ts=t.values).sort_values("ts")
    at = lambda hh: b[b.h == hh].drop_duplicates("symbol").set_index("symbol")
    b930, b940 = at(9.5), at(9.5 + 10/60)
    win = b[(b.h >= 9.5) & (b.h < 9.75)]
    pre = b[b.h < 9.5]
    rth = b[(b.h >= 9.5) & (b.h < close_h)]
    gw, gp, gr = win.groupby("symbol"), pre.groupby("symbol"), rth.groupby("symbol")
    out = pd.DataFrame({
        # AT0945 -- exact bars, NaN if the bar is missing
        "o930": b930.open, "c940": b940.close,
        "h15": gw.high.max(), "l15": gw.low.min(), "v15": gw.volume.sum(),
        "n15": gw.size(), "r1": b930.high - b930.low,
        "pre_hi": gp.high.max(), "pre_lo": gp.low.min(),
        "pre_dv": (pre.close * pre.volume).groupby(pre.symbol).sum(),
        # EOD -- lagged use only
        "rth_o": gr.open.first(), "rth_hi": gr.high.max(),
        "rth_lo": gr.low.min(), "rth_c": gr.close.last(),
    })
    out.loc[out.n15 != 3, ["h15","l15","v15"]] = np.nan      # a partial window is not a window
    return out.drop(columns="n15")

def main():
    pool = pd.read_parquet("cache/intraday_pool.parquet")
    pool = pool[(pool.rk <= 100) & (pool.date < HOLDOUT_START)]
    names = set(pool.symbol)
    stk = sorted(glob.glob("cache/mp5min/*.parquet"))
    etf = {f.split("_")[-1][:10]: f for f in glob.glob("cache/mp_etf_5min/*.parquet")}
    S, E, t0, halves = [], [], time.time(), 0
    for i, f in enumerate(stk):
        day = pd.Timestamp(f.split("_")[-1][:10])
        if day >= HOLDOUT_START: break                           # sealed
        d = pd.read_parquet(f, columns=COLS).dropna(subset=["symbol"])
        if d.symbol.nunique() < 1000: continue                   # vendor holiday file
        close_h = session_close(d); halves += close_h < 16
        s = summarise(d[d.symbol.isin(names)], close_h); s["date"] = day; S.append(s.reset_index())
        e = pd.read_parquet(etf[str(day.date())], columns=COLS)
        e = summarise(e[e.symbol.isin(ETFS)], close_h); e["date"] = day; E.append(e.reset_index())
        if i % 100 == 0: print(f"  {i}/{len(stk)}  {day.date()}  {time.time()-t0:.0f}s", flush=True)
    S, E = pd.concat(S, ignore_index=True), pd.concat(E, ignore_index=True)
    assert_sealed(S.date); assert_sealed(E.date)
    S.to_parquet("cache/sel_stocks.parquet", index=False); E.to_parquet("cache/sel_etfs.parquet", index=False)
    print(f"{len(S):,} stock rows, {S.symbol.nunique()} names, {S.date.nunique()} sessions "
          f"({S.date.min().date()} -> {S.date.max().date()}); {halves} early closes; {len(E):,} ETF rows  ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    main()
