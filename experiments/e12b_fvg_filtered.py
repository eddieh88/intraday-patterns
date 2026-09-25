"""E12b: FVGs with the DISPLACEMENT filter practitioners actually require.

E12 counted every 3-bar non-overlap: 2.4M gaps, 16.6 per name-day, median width
0.067% -- a third of one bar.  That is not what anyone means by a fair value
gap; it is tick noise catalogued.

The practitioner definition adds conditions:
  * the middle candle is a DISPLACEMENT -- range >= DISP x the recent average,
    and it closes in the top/bottom third of its own range (a decisive move)
  * the gap is of meaningful WIDTH relative to the bar size
  * (often) it forms after a break of structure, in the trend direction

Reported across a grid of displacement and width thresholds, so the effect of
each filter is visible rather than baked in.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, "lib")
from intraday_levels import session_frames

def gaps(o,h,l,c,atr,disp,minw):
    out=[]
    for i in range(len(h)-2):
        m=i+1
        rng=h[m]-l[m]
        if not np.isfinite(atr[m]) or atr[m]<=0: continue
        if rng < disp*atr[m]: continue                      # displacement candle
        body_pos = (c[m]-l[m])/rng if rng>0 else .5
        if h[i] < l[i+2]:
            if body_pos < 0.67: continue                    # must close decisively up
            w=(l[i+2]-h[i])/h[i]
            if w >= minw*atr[m]/c[m]: out.append((i+2,h[i],l[i+2],w))
        elif l[i] > h[i+2]:
            if body_pos > 0.33: continue
            w=(l[i]-h[i+2])/l[i]
            if w >= minw*atr[m]/c[m]: out.append((i+2,h[i+2],l[i],w))
    return out

def track(h,l,lo,hi,start):
    tap=half=full=False; mid=(lo+hi)/2
    for j in range(start+1,len(h)):
        if l[j]<=hi and h[j]>=lo: tap=True
        if l[j]<=mid<=h[j]: half=True
        if l[j]<=lo and h[j]>=hi: full=True; break
    return tap,half,full

files=sorted(glob.glob("cache/mp5min/*.parquet"))[::4]
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
GRID=[(1.0,0.0,"none (E12's definition)"),(1.5,0.25,"disp 1.5x, w>=0.25 ATR"),
      (2.0,0.5,"disp 2.0x, w>=0.5 ATR"),(2.5,0.75,"disp 2.5x, w>=0.75 ATR"),
      (3.0,1.0,"disp 3.0x, w>=1.0 ATR")]
acc={g[2]:[] for g in GRID}
t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<60: continue
    o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
    pc=np.concatenate([[c[0]],c[:-1]])
    atr=pd.Series(np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))).rolling(14,min_periods=5).mean().values
    for disp,minw,lab in GRID:
        for idx,lo,hi,w in gaps(o,h,l,c,atr,disp,minw):
            tap,half,full=track(h,l,lo,hi,idx)
            acc[lab].append((w,tap,half,full))
    if i%20000==0 and i: print(f"  {i:,} sessions, {time.time()-t0:.0f}s",flush=True)

nsess=len({1})
print(f"\n{'filter':26s}{'n gaps':>11s}{'per name-day':>14s}{'med width':>11s}"
      f"{'tap':>8s}{'50%':>8s}{'full':>8s}")
print("-"*90)
tot_days=len(files)*len(NAMES)
for disp,minw,lab in GRID:
    a=np.array([(w,t,hf,f) for w,t,hf,f in acc[lab]],dtype=float)
    if len(a)<100: print(f"{lab:26s}{len(a):>11,}  (too few)"); continue
    print(f"{lab:26s}{len(a):11,}{len(a)/tot_days:14.2f}{np.median(a[:,0]):11.3%}"
          f"{a[:,1].mean():8.1%}{a[:,2].mean():8.1%}{a[:,3].mean():8.1%}")
print(f"\npublished benchmarks                            74.6%   61.2%   48.7%")
print(f"\nsame-session only, so these read lower than multi-day figures.")
