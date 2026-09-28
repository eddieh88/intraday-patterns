"""E12: fair value gaps -- correct definition, and do the published fill rates hold?

A fair value gap is THREE CONSECUTIVE candles where the first and third do not
overlap:
    bullish   high[i] < low[i+2]      gap = (high[i], low[i+2])
    bearish   low[i]  > high[i+2]     gap = (high[i+2], low[i])
The middle candle moves far enough that no two-sided trade happened inside the
band.  An earlier version of this compared bar i to bar i+24 and ignored the
bars between -- that is not an FVG and its results were void.

Published practitioner benchmarks to test against:
    74.6%  receive an initial edge tap
    61.2%  reach the 50% midpoint
    48.7%  fully close
There is no peer-reviewed literature on FVG as such; the related academic work
is on order-flow imbalance and gap filling.

Measured on 5-minute and on 1-hour bars (resampled), RTH only, same 100 names.
A gap is tracked until the end of the NEXT session.
"""
import pandas as pd, numpy as np, glob, sys, time
from intraday_levels import session_frames

def find_fvg(h,l,minw=0.0):
    """-> list of (index, lo_edge, hi_edge, direction)"""
    out=[]
    for i in range(len(h)-2):
        if h[i] < l[i+2] and (l[i+2]-h[i])/h[i] > minw:
            out.append((i+2, h[i], l[i+2], +1))          # bullish
        elif l[i] > h[i+2] and (l[i]-h[i+2])/l[i] > minw:
            out.append((i+2, h[i+2], l[i], -1))          # bearish
    return out

def track(h,l,lo,hi,start):
    """-> (tapped, half, full) over the remaining bars"""
    tap=half=full=False
    mid=(lo+hi)/2
    for j in range(start+1,len(h)):
        if l[j]<=hi and h[j]>=lo: tap=True
        if l[j]<=mid<=h[j] or (l[j]<=mid and h[j]>=mid): half=True
        if l[j]<=lo and h[j]>=hi: full=True
        elif l[j]<=lo or h[j]>=hi:
            # price traversed the whole band from one side
            if (l[j]<=lo and h[j]>=hi) or (h[j]>=hi and l[j]<=lo): full=True
        if full: break
    return tap,half,full

files=sorted(glob.glob("cache/mp5min/*.parquet"))
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<60: continue
    for tf,frame in (("5min",rth),
                     ("1hour",rth.set_index("ts").resample("1h").agg(
                        {"open":"first","high":"max","low":"min","close":"last"}).dropna().reset_index())):
        h=frame.high.values.astype(float); l=frame.low.values.astype(float)
        if len(h)<6: continue
        span=((h-l)/frame.close.values).mean()
        for idx,lo,hi,d in find_fvg(h,l):
            w=(hi-lo)/lo
            tap,half,full=track(h,l,lo,hi,idx)
            rows.append(dict(tf=tf,dir=d,width=w,rel=w/span if span>0 else np.nan,
                             tap=tap,half=half,full=full,bars_left=len(h)-idx))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} gaps, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e12_fvg.parquet",index=False)
print(f"\n{len(T):,} fair value gaps  ({time.time()-t0:.0f}s)\n")
print(f"{'timeframe':12s}{'n':>9s}{'edge tap':>11s}{'50% mid':>10s}{'full close':>12s}{'med width':>11s}")
print("-"*66)
for tf,g_ in T.groupby("tf"):
    print(f"{tf:12s}{len(g_):9,}{g_.tap.mean():11.1%}{g_.half.mean():10.1%}"
          f"{g_.full.mean():12.1%}{g_.width.median():11.3%}")
print(f"{'published':12s}{'':9s}{0.746:11.1%}{0.612:10.1%}{0.487:12.1%}")
print("\nBY GAP WIDTH relative to the average bar of that timeframe (5-min):")
f5=T[T.tf=="5min"]
print(f"{'width':16s}{'n':>9s}{'edge tap':>11s}{'50% mid':>10s}{'full close':>12s}")
for lo,hi,lab in ((0,1,"< 1 bar"),(1,2,"1-2 bars"),(2,4,"2-4 bars"),(4,99,"> 4 bars")):
    x=f5[(f5.rel>=lo)&(f5.rel<hi)]
    if len(x)<200: continue
    print(f"{lab:16s}{len(x):9,}{x.tap.mean():11.1%}{x.half.mean():10.1%}{x.full.mean():12.1%}")
print("\nNote: gaps are tracked only to the session close, so these are")
print("SAME-SESSION fill rates and will read lower than multi-day benchmarks.")
