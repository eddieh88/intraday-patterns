"""Paired test: SAME events, two entry timings.

Comparing all breakouts against the subset that retested confounds entry timing
with which breakouts produce retests.  Here each event contributes BOTH trades,
so the difference is purely the timing.
"""
import numpy as np, pandas as pd, warnings, sys
from scipy import stats
warnings.filterwarnings("ignore"); sys.path.insert(0, "lib")
from setups_v2 import (pivots, horiz_level, trendline, struct_stop,
                       K, LOOKBACK, CLUST, BUF, RWIN, MAXBARS, PAD, MIN_GAP, MIN_ADV)
RR=3.0
def trade(o,h,l,c,e,stop,rr=RR,cost_bp=10):
    entry=c[e]; risk=entry-stop
    if not np.isfinite(risk) or risk<=0 or risk/entry<0.002: return None
    tgt=entry+rr*risk; cost=(cost_bp*1e-4)*entry*2
    for i in range(e+1,min(e+1+MAXBARS,len(c))):
        if l[i]<=stop:  return (min(stop,o[i])-entry-cost)/risk
        if h[i]>=tgt:   return (max(tgt,o[i])-entry-cost)/risk
    j=min(e+MAXBARS,len(c)-1); return (c[j]-entry-cost)/risk

df=pd.read_parquet("colab/colab_ohlcv.parquet").sort_values(["symbol","timestamp"])
P={"H":[], "T":[]}
for s,g in df.groupby("symbol",sort=False):
    o,h,l,c=(g[k].values.astype(float) for k in ("open","high","low","close"))
    bad=g.bad_day.values; n=len(c)
    if n<LOOKBACK+RWIN+MAXBARS+2*K+2: continue
    ph=np.flatnonzero(pivots(h,K,"high")); pl=np.flatnonzero(pivots(l,K,"low"))
    for b in range(LOOKBACK,n-MAXBARS-1):
        if bad[max(0,b-LOOKBACK):b+MAXBARS+1].any(): continue
        for kind,lvl in (("H",horiz_level(b,ph,h)),("T",trendline(b,ph,h))):
            if lvl is None or not np.isfinite(lvl) or lvl<=0: continue
            if not (c[b-1]<=lvl*(1+BUF)<c[b]): continue
            zone=lvl
            if kind=="T":
                R2=horiz_level(b,ph,h)
                if R2 is not None and np.isfinite(R2) and R2>0: zone=R2
            for r in range(b+MIN_GAP,min(b+1+RWIN,n-MAXBARS)):
                if h[b+1:r].size and (h[b+1:r].max()-zone)/zone < MIN_ADV: continue
                if l[r]<=zone*(1+CLUST/2):
                    if c[r]>zone:                      # a genuine bounce happened
                        sb=struct_stop(b,pl,l); sr=struct_stop(r,pl,l)
                        if sb is None or sr is None: break
                        ta=trade(o,h,l,c,b,sb); tb=trade(o,h,l,c,r,sr)
                        if ta is not None and tb is not None: P[kind].append((ta,tb))
                    break
print(f"{'family':10s}{'n pairs':>9s}{'at break':>11s}{'at retest':>11s}{'diff':>10s}{'t (paired)':>12s}")
print("-"*64)
for k in ("H","T"):
    a=np.array([x[0] for x in P[k]]); b_=np.array([x[1] for x in P[k]])
    if len(a)<50: continue
    d=b_-a; t=d.mean()/(d.std(ddof=1)/np.sqrt(len(d)))
    print(f"{k:10s}{len(a):9,}{a.mean():+11.3f}{b_.mean():+11.3f}{d.mean():+10.3f}{t:+12.2f}")
print("\nSAME events, only the entry bar differs -- so this isolates the timing.")
