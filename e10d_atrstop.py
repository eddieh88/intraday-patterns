"""E10d: E10c with the literature-standard stop -- 2 x ATR(14), not 2 x entry bar.

E10c used 2 x the entry BAR's range.  That lands between 1.5x and 2x ATR in
magnitude and correlates 0.83 with ATR, but a single bar is a noisy volatility
estimate (p90/p10 of 5.7x vs 4.6x for ATR).  The standard, from the Turtles'
2N rule, is 2 x ATR; reviews spanning 1980-2024 find volatility-adaptive stops
beat fixed-percentage ones by 25-45% in Sharpe.

The martingale argument says expectancy is zero for ANY stop placement on a
driftless walk, so this should change nothing.  Verifying rather than asserting.

E10/E10b were long-only, so their slightly positive gross (+0.015R) was market
drift, not entry quality.  A long-only test cannot separate "this entry finds
good trades" from "the market went up".

Here every entry has a long and a short form, and the diagnostic is the
LONG MINUS SHORT spread:

  drift shows up equally in every arm, so it cancels in the spread
  a real directional signal shows up as a spread LARGER than random's

  random         a uniform bar, traded long; and another traded short
  level          break above PMH + retest (long) / below PML + retest (short)
  ORB            break of the 09:30-10:00 high (long) / low (short)
  VWAP           first close back above VWAP (long) / below (short)
  pullback       first down bar after a >0.5% run up (long) /
                 first up bar after a >0.5% run down (short)

2-bar stop, 3R target, 1bp round trip -- the corrected friction from E10b.
"""
import pandas as pd, numpy as np, glob, sys, time
from scipy import stats
sys.path.insert(0, ".")
from intraday_levels import session_frames
COST_BP, MAXB = 1.0, 60
rng=np.random.default_rng(0)

def trade(o,h,l,c,atr,e,up):
    entry=c[e]; bar=atr[e] if np.isfinite(atr[e]) else (h[e]-l[e])
    stop = entry-2*bar if up else entry+2*bar
    risk=abs(entry-stop)
    if risk<=0 or risk/entry<0.0003: return None
    tgt = entry+3*risk if up else entry-3*risk
    cost=COST_BP*1e-4*entry; end=min(len(c),e+1+MAXB)
    for j in range(e+1,end):
        if up:
            if l[j]<=stop: return (min(stop,o[j])-entry-cost)/risk
            if h[j]>=tgt:  return (max(tgt,o[j])-entry-cost)/risk
        else:
            if h[j]>=stop: return (entry-max(stop,o[j])-cost)/risk
            if l[j]<=tgt:  return (entry-min(tgt,o[j])-cost)/risk
    return ((c[end-1]-entry) if up else (entry-c[end-1]))/risk - cost/risk

files=sorted(glob.glob("cache/mp5min/*.parquet"))
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
D=D[D.symbol.isin(NAMES)]
prior={(r.symbol,r.date):(r.pdh,r.pdl) for r in D.itertuples()}
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    pre=g[g.h<9.5]; rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<40 or len(pre)<5: continue
    o,h,l,c,v=(rth[k].values.astype(float) for k in ("open","high","low","close","volume"))
    hh=rth.h.values
    pc=np.concatenate([[c[0]],c[:-1]])
    atr=pd.Series(np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))).rolling(14,min_periods=5).mean().values
    vwap=np.cumsum(((h+l+c)/3)*v)/np.maximum(np.cumsum(v),1)
    win=np.flatnonzero((hh>=9.5)&(hh<11.5))
    if len(win)<6: continue
    pmh,pml=pre.high.max(),pre.low.min()
    orh=h[hh<10].max() if (hh<10).any() else np.nan
    orl=l[hh<10].min() if (hh<10).any() else np.nan
    ent={}
    ent[("random",True)]  = [int(rng.choice(win))]
    ent[("random",False)] = [int(rng.choice(win))]
    for up,lvl in ((True,pmh),(False,pml)):
        brk=None
        for j in win:
            if (up and c[j]>lvl) or ((not up) and c[j]<lvl): brk=int(j); break
        if brk is None: continue
        for r_ in range(brk+3,min(brk+16,len(c))):
            adv = (h[brk+1:r_].max()-lvl)/lvl if up else (lvl-l[brk+1:r_].min())/lvl
            if r_>brk+1 and adv<0.0018: continue
            if (up and l[r_]<=lvl and c[r_]>lvl) or ((not up) and h[r_]>=lvl and c[r_]<lvl):
                ent[("level",up)]=[r_]; break
    ent[("ORB",True)]  = [int(j) for j in win if hh[j]>=10 and c[j]>orh][:1]
    ent[("ORB",False)] = [int(j) for j in win if hh[j]>=10 and c[j]<orl][:1]
    ent[("VWAP",True)] = [int(j) for j in win if j>2 and c[j-1]<vwap[j-1] and c[j]>vwap[j]][:1]
    ent[("VWAP",False)]= [int(j) for j in win if j>2 and c[j-1]>vwap[j-1] and c[j]<vwap[j]][:1]
    ent[("pullback",True)] = [int(j) for j in win if j>3 and (h[:j].max()/o[0]-1)>0.005 and c[j]<o[j]][:1]
    ent[("pullback",False)]= [int(j) for j in win if j>3 and (1-l[:j].min()/o[0])>0.005 and c[j]>o[j]][:1]
    for (k,up),idx in ent.items():
        for e in idx:
            if e>=len(c)-8: continue
            r_=trade(o,h,l,c,atr,e,up)
            if r_ is not None: rows.append(dict(entry=k,up=up,R=r_))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} trades, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e10d_atrstop.parquet",index=False)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")
print(f"{'entry':12s}{'n long':>9s}{'long R':>9s}{'n short':>9s}{'short R':>9s}"
      f"{'L-S spread':>13s}{'t':>8s}")
print("-"*70)
sp={}
for k,g_ in T.groupby("entry"):
    L=g_[g_.up].R.values; S=g_[~g_.up].R.values
    if len(L)<200 or len(S)<200: continue
    t,_=stats.ttest_ind(L,S,equal_var=False)
    sp[k]=L.mean()-S.mean()
    print(f"{k:12s}{len(L):9,}{L.mean():+9.3f}{len(S):9,}{S.mean():+9.3f}"
          f"{L.mean()-S.mean():+13.3f}{t:+8.2f}")
print("-"*70)
if "random" in sp:
    print(f"\nrandom's long-short spread is the DRIFT baseline: {sp['random']:+.3f}R")
    print("an entry with real directional signal must exceed it:\n")
    for k,v in sorted(sp.items(),key=lambda x:-x[1]):
        if k=="random": continue
        print(f"  {k:12s} spread {v:+.3f}R   excess over drift {v-sp['random']:+.3f}R")
