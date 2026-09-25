"""Targets and trade results for prereg/selection.md (Amendment 3), development only.

The only code in the study that reads bars at or after 09:45 -- legitimately,
since these are outcomes. One row per name-day in the feature table:

  y        side x (10:55 close - 09:45 open) / 1R      signed continuation
  er       |10:55 close - 09:45 open| / path length    efficiency ratio, sign-free
  r_gross  the bracketed trade: -1R / +2R / 11:00, stop first on a tie, gaps fill at the open
  net_a3   r_gross - 3bp x fill / 1R                    cost through the trade's own 1R
  net_a6   r_gross - 6bp x fill / 1R
  net_b    r_gross - 0.023R                             flat cost in R

  python3 selection/outcomes.py   -> cache/sel_outcomes.parquet
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, "lib")
from holdout import HOLDOUT_START, assert_sealed

COLS = ["timestamp","symbol","open","high","low","close","volume"]
FLOOR_BP, COST_B = 10.0, 0.023

def trade(o, h, l, c, side, R):
    fill = o[0]
    stop, tgt = fill - side * R, fill + 2 * side * R
    for j in range(len(o)):
        hit_stop = l[j] <= stop if side > 0 else h[j] >= stop
        hit_tgt  = h[j] >= tgt  if side > 0 else l[j] <= tgt
        if hit_stop:
            px = min(stop, o[j]) if side > 0 else max(stop, o[j]); return side * (px - fill) / R, "stop"
        if hit_tgt:
            px = max(tgt, o[j]) if side > 0 else min(tgt, o[j]);   return side * (px - fill) / R, "target"
    return side * (c[-1] - fill) / R, "time"

def main():
    F = pd.read_parquet("cache/sel_features.parquet", columns=["date","symbol","side","R_bp"])
    S = pd.read_parquet("cache/sel_stocks.parquet", columns=["date","symbol","h15","l15"])
    F = F.merge(S, on=["date","symbol"]); F["R"] = F.h15 - F.l15
    n0 = len(F); F = F[F.R_bp >= FLOOR_BP]; floor_dropped = n0 - len(F)
    assert_sealed(F.date)
    by_day = {d: g.set_index("symbol") for d, g in F.groupby("date")}
    out, missing, t0 = [], 0, time.time()
    for i, f in enumerate(sorted(glob.glob("cache/mp5min/*.parquet"))):
        day = pd.Timestamp(f.split("_")[-1][:10])
        if day >= HOLDOUT_START: break
        if day not in by_day: continue
        rows = by_day[day]
        b = pd.read_parquet(f, columns=COLS).dropna(subset=["symbol"])
        b = b[b.symbol.isin(rows.index)]
        t = pd.to_datetime(b.timestamp); h = (t.dt.hour + t.dt.minute/60).values
        b = b.assign(h=h, ts=t.values)
        b = b[(b.h >= 9.75) & (b.h < 11.0)].sort_values("ts")
        got = set()
        for sym, g in b.groupby("symbol"):
            if g.h.iloc[0] != 9.75 or abs(g.h.iloc[-1] - (10 + 55/60)) > 1e-9: continue
            r = rows.loc[sym]; side, R = float(r.side), float(r.R)
            o, hi, lo, c = (g[k].values.astype(float) for k in ("open","high","low","close"))
            fill = o[0]
            path = np.abs(np.diff(np.concatenate([[fill], c]))).sum()
            rg, how = trade(o, hi, lo, c, side, R)
            out.append(dict(date=day, symbol=sym, fill=fill, y=side * (c[-1] - fill) / R,
                            er=abs(c[-1] - fill) / path if path > 0 else np.nan, r_gross=rg, exit=how,
                            net_a3=rg - 3e-4 * fill / R, net_a6=rg - 6e-4 * fill / R, net_b=rg - COST_B))
            got.add(sym)
        missing += len(rows) - len(got)
        if i % 200 == 0: print(f"  {day.date()}  {len(out):,}  {time.time()-t0:.0f}s", flush=True)
    O = pd.DataFrame(out); assert_sealed(O.date)
    O.to_parquet("cache/sel_outcomes.parquet", index=False)
    print(f"{len(O):,} name-days with outcomes; dropped: {floor_dropped} under the {FLOOR_BP:.0f}bp floor, "
          f"{missing} missing the 09:45 or 10:55 bar  ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    main()
