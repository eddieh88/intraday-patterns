"""Run the retest detector on real sessions -- development period only.

Levels, ATR and the 09:30 open come from the selection study's stage A table
(cache/sel_stocks.parquet), which is half-day aware and development-only.

  python3 retest/run.py   -> cache/retest_rows.parquet
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, "retest"); sys.path.insert(0, "selection"); sys.path.insert(0, "lib")
import detect as D
from session_summary import session_close
from holdout import HOLDOUT_START, assert_sealed

COLS = ["timestamp","symbol","open","high","low","close","volume"]

def main():
    pool = pd.read_parquet("cache/intraday_pool.parquet")
    pool = pool[(pool.rk <= 100) & (pool.date < HOLDOUT_START)]
    by_day = pool.groupby("date").symbol.apply(set)
    S = pd.read_parquet("cache/sel_stocks.parquet")
    W = {c: S.pivot(index="date", columns="symbol", values=c).sort_index()
         for c in ("rth_hi","rth_lo","pre_hi","pre_lo","o930")}
    lv = {"PDH": W["rth_hi"].shift(1), "PDL": W["rth_lo"].shift(1),
          "P2H": W["rth_hi"].shift(2), "P2L": W["rth_lo"].shift(2),
          "PMH": W["pre_hi"], "PML": W["pre_lo"]}
    atr = (W["rth_hi"] - W["rth_lo"]).rolling(14, min_periods=10).mean().shift(1)
    rows, t0 = [], time.time()
    files = [f for f in sorted(glob.glob("cache/mp5min/*.parquet"))
             if pd.Timestamp(f.split("_")[-1][:10]) in by_day.index]
    for i, f in enumerate(files):
        day = pd.Timestamp(f.split("_")[-1][:10])
        full = pd.read_parquet(f, columns=COLS).dropna(subset=["symbol"])
        close_h = session_close(full)
        d = full[full.symbol.isin(by_day[day])]
        t = pd.to_datetime(d.timestamp)
        d = d.assign(h=(t.dt.hour + t.dt.minute/60).values, ts=t.values).sort_values("ts")
        for sym, g in d.groupby("symbol"):
            a = atr.at[day, sym] if sym in atr.columns else np.nan
            o930 = W["o930"].at[day, sym] if sym in W["o930"].columns else np.nan
            if not (np.isfinite(a) and a > 0 and np.isfinite(o930)): continue
            pre = g[g.h < 9.5]; rth = g[(g.h >= 9.5) & (g.h < close_h)]
            if len(rth) < 20: continue
            prev_close = pre.close.iloc[-1] if len(pre) else np.nan
            o, h, l, c = (rth[k].values.astype(float) for k in ("open","high","low","close"))
            hours = rth.h.values
            real, fake = D.levels(*(lv[k].at[day, sym] for k in ("PDH","PDL","P2H","P2L","PMH","PML")), o930)
            for kind, levels in (("real", real), ("fake", fake)):
                for name, L in levels:
                    first, retest = D.scan(o, h, l, c, hours, prev_close, L, a)
                    for stage, r in (("first", first), ("retest", retest)):
                        if r: rows.append(dict(date=day, symbol=sym, kind=kind, level=name, stage=stage, **r))
        if i % 100 == 0: print(f"  {i}/{len(files)}  {day.date()}  {len(rows):,} rows  {time.time()-t0:.0f}s", flush=True)
    R = pd.DataFrame(rows); assert_sealed(R.date)
    R.to_parquet("cache/retest_rows.parquet", index=False)
    print(f"{len(R):,} scored touches over {R.date.nunique()} sessions  ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    main()
