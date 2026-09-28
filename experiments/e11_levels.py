"""E11: do price REACTIONS at marked levels differ from reactions at random prices?

The claim: "we wait at OUR levels, nowhere else."  That is testable -- when
price arrives at a marked level, something should happen that does not happen
at an arbitrary price.

Levels (all known before 09:30):
  PDH / PDL   prior session high / low
  PMH / PML   pre-market 04:00-09:30 high / low  (a weak London proxy -- the
              real London session starts 03:00 and this window carries only
              8% of daily volume)
  NWOG        Friday close -> Monday open gap, Mondays only
  FVG         1-hour fair value gap: a 3-bar window where bar1.high < bar3.low
              (bullish) leaves an unfilled zone; we mark its edge

CONTROL, and this is the whole test: for every real level we also place a
SYNTHETIC level at the same distance from the 09:30 open, offset to a random
price that is not one of the marked ones.  Levels near the current price get
touched more often and the post-touch move differs mechanically, so a control
matched on distance is the only fair comparison.

TWO statistics, because there are two distinct claims:

  DIRECTION  after price first touches the level from below during 09:30-11:30,
             the move over the next 12 bars, signed so POSITIVE = rejected.
             Tests "price reverses at levels."

  ACTIVITY   volume and bar range AT the touch bar and the 3 bars after,
             relative to that day's own average for that symbol.
             Tests "levels are where the action is" -- stops and resting orders
             cluster at obvious prices, so more should execute there.

These can disagree, and the disagreement matters: a level that concentrates
volatility without predicting direction is a good place to trade FROM but
supplies no edge by itself.
"""
import pandas as pd, numpy as np, glob, sys, time
from intraday_levels import session_frames
HOLD, T0, T1 = 12, 9.5, 11.5
rng=np.random.default_rng(0)

def fvg_levels(h,l,step=12):
    """1-hour FVGs from 5-min bars: h[i] < l[i+2*step] leaves an unfilled zone"""
    out=[]
    for i in range(0,len(h)-2*step,step):
        a,b=i,i+2*step
        if b<len(l) and h[a]<l[b]: out.append(l[b])      # bullish FVG lower edge
        if b<len(h) and l[a]>h[b]: out.append(h[b])      # bearish FVG upper edge
    return out

def react(h,l,c,hh,L,hold=HOLD):
    """first touch of L from below during the window -> signed move away from L"""
    for j in range(len(c)):
        if not (T0<=hh[j]<T1): continue
        if j==0 or h[j-1]>=L: continue          # must approach from below
        if h[j]>=L>l[j] or (h[j]>=L and c[j-1]<L):
            k=min(j+hold,len(c)-1)
            return -(c[k]-L)/L, j               # positive = pushed back DOWN
    return None,None

def activity(h,l,c,v,j,span=4):
    """volume and range at the touch, relative to the session's own average"""
    if j is None: return np.nan,np.nan
    k=min(j+span,len(c))
    rng_=((h[j:k]-l[j:k])/c[j:k]).mean()
    base_r=((h-l)/c).mean(); base_v=v.mean()
    return (v[j:k].mean()/base_v if base_v>0 else np.nan,
            rng_/base_r if base_r>0 else np.nan)

files=sorted(glob.glob("cache/mp5min/*.parquet"))
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
D=D[D.symbol.isin(NAMES)]
prior={(r.symbol,r.date):(r.pdh,r.pdl,r.pdc) for r in D.itertuples()}
prevclose={}
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    key=(s,dt)
    if key not in prior: continue
    pdh,pdl,pdc=prior[key]
    pre=g[g.h<9.5]; rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<40 or len(pre)<5: continue
    h,l,c,v=(rth[k].values.astype(float) for k in ("high","low","close","volume"))
    hh=rth.h.values; op=rth.open.values[0]
    ph,pl=(pre.high.max(),pre.low.min())
    marks={"PDH":pdh,"PML":pl,"PMH":ph}
    if dt.dayofweek==0 and np.isfinite(pdc): marks["NWOG"]=pdc
    for fv in fvg_levels(h,l)[:2]: marks[f"FVG"]=fv
    for name,L in marks.items():
        if L is None or not np.isfinite(L) or L<=0 or L<=op: continue   # above the open only
        r,j=react(h,l,c,hh,L)
        if r is None: continue
        d_=(L-op)/op
        # matched control: same distance, random sign-preserving jitter, not a marked price
        for attempt in range(6):
            Lc=op*(1+d_*rng.uniform(0.6,1.4))
            if all(abs(Lc-m)/max(m,1e-9)>0.002 for m in marks.values() if m and np.isfinite(m)): break
        rc,jc=react(h,l,c,hh,Lc)
        av,ar=activity(h,l,c,v,j); cv,cr=activity(h,l,c,v,jc)
        rows.append(dict(sym=s,date=dt,level=name,dist=d_,real=r,ctrl=rc,
                         vol_real=av,rng_real=ar,vol_ctrl=cv,rng_ctrl=cr))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} touches, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e11_levels.parquet",index=False)
print(f"\n{len(T):,} level-touches  ({time.time()-t0:.0f}s)\n")
print(f"{'level':10s}{'n':>9s}{'real react':>12s}{'ctrl react':>12s}{'diff':>10s}{'t(paired)':>11s}")
print("-"*66)
for k,g_ in T.groupby("level"):
    p=g_.dropna(subset=["real","ctrl"])
    if len(p)<200: continue
    d=(p.real-p.ctrl).values
    print(f"{k:10s}{len(p):9,}{p.real.mean()*100:+12.4f}{p.ctrl.mean()*100:+12.4f}"
          f"{d.mean()*100:+10.4f}{d.mean()/(d.std()/np.sqrt(len(d))):+11.2f}")
print("\n'react' = % move AWAY from the level over the next hour; positive = rejected.\n")
print("ACTIVITY AT THE TOUCH  (volume and range vs that session's own average)")
print(f"{'level':10s}{'n':>9s}{'vol real':>11s}{'vol ctrl':>11s}{'rng real':>11s}{'rng ctrl':>11s}{'t(vol)':>9s}")
print("-"*72)
for k,g_ in T.groupby("level"):
    p=g_.dropna(subset=["vol_real","vol_ctrl"])
    if len(p)<200: continue
    d=(p.vol_real-p.vol_ctrl).values
    print(f"{k:10s}{len(p):9,}{p.vol_real.mean():11.2f}{p.vol_ctrl.mean():11.2f}"
          f"{p.rng_real.mean():11.2f}{p.rng_ctrl.mean():11.2f}"
          f"{d.mean()/(d.std()/np.sqrt(len(d))):+9.2f}")
print("\n1.00 = the session average.  If levels concentrate activity, real > ctrl")
print("even where the DIRECTIONAL test above shows nothing.")
