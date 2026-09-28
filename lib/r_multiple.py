"""Evaluate setups as 1R:3R bracket trades, not fixed-horizon returns.

A bracket exits on whichever barrier is touched first, so mean forward return is
the wrong statistic.  At 3:1 you break even at a 25% hit rate, so a setup with a
negative 5-day mean can still be profitable, and one with a positive mean can
still lose.

  entry  : close of the entry bar
  stop   : just below that bar's low (the retest low) -> risk R = entry - stop
  target : entry + RR * R
  first touch wins; if a bar spans both, the STOP is assumed first (conservative)
  if neither within MAXBARS, mark to market at that close, in R units
"""
import numpy as np, pandas as pd
from swing_levels import scan_trades

RR, MAXBARS, PAD = 3.0, 20, 0.002

def bracket(h, l, c, e, rr=RR, maxbars=MAXBARS, pad=PAD):
    """-> R multiple of the trade entered at close[e]"""
    entry = c[e]; stop = l[e]*(1-pad); risk = entry-stop
    if not np.isfinite(risk) or risk <= 0: return None
    target = entry + rr*risk
    for i in range(e+1, min(e+1+maxbars, len(c))):
        if l[i] <= stop:  return -1.0                 # stop first if both hit
        if h[i] >= target: return rr
    j = min(e+maxbars, len(c)-1)
    return (c[j]-entry)/risk

def summarise(name, rs):
    rs = np.array([r for r in rs if r is not None])
    if len(rs) < 50: return
    win = (rs > 0).mean(); exp = rs.mean()
    be  = 1.0/(1.0+RR)
    print(f"{name:14s}{len(rs):8,}{win:9.1%}{be:11.1%}{exp:+11.3f}"
          f"{rs.std()/np.sqrt(len(rs)):9.3f}{exp/(rs.std()/np.sqrt(len(rs))):+8.2f}")

if __name__ == "__main__":
    df = pd.read_parquet("colab/colab_ohlcv.parquet")
    df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
    buckets = {k: [] for k in ("bounce","immediate","failure","no_breakout")}
    for j,(s,g) in enumerate(df.groupby("symbol", sort=False)):
        h,l,c = (g[k].values.astype(float) for k in ("high","low","close"))
        for kind, e in scan_trades(g):
            buckets[kind].append(bracket(h,l,c,e))
        if j % 150 == 0: print(f"  {j} names", flush=True)
    print(f"\n{RR:.0f}R target, 1R stop below the entry bar's low, {MAXBARS}-bar time limit")
    print(f"{'setup':14s}{'n':>8s}{'win rate':>9s}{'breakeven':>11s}{'exp (R)':>11s}{'SE':>9s}{'t':>8s}")
    print("-"*70)
    for k in ("bounce","immediate","failure","no_breakout"):
        summarise(k, buckets[k])
