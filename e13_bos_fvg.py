"""E13: break of structure -> FVG -> tap entry.  Rules in PREREG_bos_fvg.md.

  1. close above PMH (pre-market high), first time in 09:30-11:00
  2. first 3-candle bullish FVG at or after that break bar
  3. entry when a later bar taps the FVG band AND closes green above the FVG low
  4. stop = low of the FVG's middle candle; target = nearest 1H swing high above
  5. skip if RR < 1
Short side mirrors it on PML.  Costs 2bp round trip, stops fill through gaps.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames
COST_BP, T0, T1, MINRR = 2.0, 9.5, 11.0, 1.0

def bull_fvg(h,l,start,end):
    for i in range(start,min(end,len(h)-2)):
        if h[i] < l[i+2]: return (i+2, h[i], l[i+2], i+1)   # (bar, lo, hi, middle)
    return None
def bear_fvg(h,l,start,end):
    for i in range(start,min(end,len(h)-2)):
        if l[i] > h[i+2]: return (i+2, h[i+2], l[i], i+1)
    return None

def swing_targets(H1h, H1l, price, up):
    """nearest 1-hour swing high above / low below the entry"""
    if up:
        c=[x for x in H1h if x>price*1.001]
        return min(c) if c else None
    c=[x for x in H1l if x<price*0.999]
    return max(c) if c else None

files=sorted(glob.glob("cache/mp5min/*.parquet"))
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
hist={}   # (sym) -> rolling list of recent 1h highs/lows
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    pre=g[g.h<9.5]; rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(pre)<5 or len(rth)<40: continue
    o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
    hh=rth.h.values
    H1=rth.set_index("ts").resample("1h").agg({"high":"max","low":"min"}).dropna()
    prevH,prevL=hist.get(s,([],[]))
    pmh,pml=pre.high.max(),pre.low.min()
    win=np.flatnonzero((hh>=T0)&(hh<T1))
    for up,lvl in ((True,pmh),(False,pml)):
        if not np.isfinite(lvl) or lvl<=0: continue
        brk=None
        for j in win:                                        # 1. close beyond the level
            if (up and c[j]>lvl) or ((not up) and c[j]<lvl): brk=int(j); break
        if brk is None: continue
        fv=(bull_fvg if up else bear_fvg)(h,l,brk,brk+18)    # 2. FVG after the break
        if fv is None: continue
        fbar,flo,fhi,fmid=fv
        ent=None
        for j in range(fbar+1,min(len(c),fbar+24)):          # 3. tap + confirmation
            if not (T0<=hh[j]<T1): continue
            if up and l[j]<=fhi and c[j]>o[j] and c[j]>flo: ent=j; break
            if (not up) and h[j]>=flo and c[j]<o[j] and c[j]<fhi: ent=j; break
        if ent is None: continue
        entry=c[ent]
        stop=(l[fmid] if up else h[fmid])                    # 4. middle candle of the FVG
        tgt=swing_targets(prevH,prevL,entry,up)
        if tgt is None: continue
        risk=abs(entry-stop)
        if risk<=0 or risk/entry<0.0005: continue
        rr=abs(tgt-entry)/risk
        if rr<MINRR: continue                                # 5. RR filter
        cost=COST_BP*1e-4*entry; res=None
        for j in range(ent+1,len(c)):
            if up:
                if l[j]<=stop: res=(min(stop,o[j])-entry-cost)/risk; break
                if h[j]>=tgt:  res=(max(tgt,o[j])-entry-cost)/risk; break
            else:
                if h[j]>=stop: res=(entry-max(stop,o[j])-cost)/risk; break
                if l[j]<=tgt:  res=(entry-min(tgt,o[j])-cost)/risk; break
        if res is None: res=((c[-1]-entry) if up else (entry-c[-1]) - 0)/risk
        rows.append(dict(sym=s,date=dt,dir="long" if up else "short",
                         rr=rr,R=res,risk_pct=risk/entry))
    hist[s]=((prevH+list(H1.high.values))[-20:], (prevL+list(H1.low.values))[-20:])
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} trades, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e13_bos_fvg.parquet",index=False)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")
def rep(lab,x):
    if len(x)<50: return
    se=x.std()/np.sqrt(len(x))
    print(f"{lab:22s}{len(x):8,}{(x>0).mean():8.1%}{x.mean():+10.3f}{np.median(x):+9.3f}{x.mean()/se:+8.2f}")
print(f"{'group':22s}{'n':>8s}{'win':>8s}{'mean R':>10s}{'median':>9s}{'t':>8s}")
print("-"*66)
rep("ALL", T.R.values)
for d,g_ in T.groupby("dir"): rep(f"  {d}", g_.R.values)
for lo,hi,lab in ((1,1.5,"RR 1.0-1.5"),(1.5,3,"RR 1.5-3  (author's ideal)"),(3,99,"RR > 3")):
    rep(f"  {lab}", T[(T.rr>=lo)&(T.rr<hi)].R.values)
print(f"\nmedian target RR {T.rr.median():.2f}   median risk {T.risk_pct.median():.2%} of price")
print(f"trades per session: {len(T)/T.date.nunique():.2f}")
