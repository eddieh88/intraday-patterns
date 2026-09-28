"""E10b: E10 re-run with a 2-BAR stop and 1bp cost.

E10 used a 0.5-bar stop, making a 2bp round trip worth 11% of the risk unit --
-0.135R of pure friction on every trade, which is why all five entries landed
in the same -0.1R band.  A decomposition showed gross (ideal fills, zero cost)
is +0.013 to +0.018R regardless of stop width, i.e. drift, and that the entire
spread came from the cost/stop interaction.

Here: stop = 2 bar ranges (risk ~0.72%), cost 1bp round trip, which is the
realistic mega-cap figure.  Friction drops to roughly -0.017R.

E8 varied exits with entries fixed and found a 0.04R spread, all negative.
This is the mirror: same two exits throughout, five different entries.

The random arm is the null for everything in E6-E8.  Van Tharp's claim is that
random entries plus good exits make money; if our real entry cannot beat a coin
toss on the same days with the same exits, it carries no information.

  random        a uniformly chosen bar between 09:30 and 11:30
  level retest  the E6 setup: prior-day level broken, advanced, retested
  ORB           break of the 09:30-10:00 range
  VWAP reclaim  first close back above session VWAP after being below it
  pullback      after a >0.5% run from the open, the first down bar

Exits: fixed 3R, and trailing 1 ATR -- the two extremes from E8.
Stop for every entry: 0.5 x the entry bar's range below the entry, so the R
denominator is constructed identically and the arms are comparable.
"""
import pandas as pd, numpy as np, glob, sys, time
from intraday_levels import session_frames, find_setups
COST_BP, MAXB = 1.0, 60
rng=np.random.default_rng(0)

def exits(o,h,l,c,e,stop):
    entry=c[e]; risk=entry-stop
    if risk<=0 or risk/entry<0.0005: return None
    cost=COST_BP*1e-4*entry; R=lambda p:(p-entry-cost)/risk
    pc=np.concatenate([[c[0]],c[:-1]])
    atr=pd.Series(np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))).rolling(14,min_periods=5).mean().values
    end=min(len(c),e+1+MAXB)
    tgt=entry+3*risk; f3=None
    for j in range(e+1,end):
        if l[j]<=stop: f3=R(min(stop,o[j])); break
        if h[j]>=tgt:  f3=R(max(tgt,o[j]));  break
    if f3 is None: f3=R(c[end-1])
    st=stop; tr=None
    for j in range(e+1,end):
        if l[j]<=st: tr=R(min(st,o[j])); break
        a=atr[j] if np.isfinite(atr[j]) else (h[j]-l[j])
        st=max(st,h[j]-a)
    if tr is None: tr=R(c[end-1])
    return f3,tr

files=sorted(glob.glob("cache/mp5min/*.parquet"))
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
D=D[D.symbol.isin(NAMES)]
prior={(r.symbol,r.date):(r.pdh,r.pdl,r.pdc) for r in D.itertuples()}
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    if (s,dt) not in prior: continue
    pdh,pdl,pdc=prior[(s,dt)]; pre=g[g.h<9.5]
    onh=pre.high.max() if len(pre) else None
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<40: continue
    o,h,l,c,v=(rth[k].values.astype(float) for k in ("open","high","low","close","volume"))
    hh=rth.h.values
    vwap=np.cumsum(((h+l+c)/3)*v)/np.maximum(np.cumsum(v),1)
    win=np.flatnonzero((hh>=9.5)&(hh<11.5))
    ents={}
    # random
    ents["random"]=[int(rng.choice(win))] if len(win) else []
    # level retest (the E6 entry)
    ents["level retest"]=[e["entry"] for e in find_setups(g,{"PDH":pdh,"PDC":pdc,"ONH":onh})
                          if e["kind"]=="bounce"]
    # ORB: first close above the 09:30-10:00 high, after 10:00
    orh=h[hh<10].max() if (hh<10).any() else np.nan
    ents["ORB"]=[int(j) for j in win if hh[j]>=10 and c[j]>orh][:1]
    # VWAP reclaim
    vr=[int(j) for j in win if j>2 and c[j-1]<vwap[j-1] and c[j]>vwap[j]]
    ents["VWAP reclaim"]=vr[:1]
    # first pullback after a >0.5% run
    pb=[int(j) for j in win if j>3 and (h[:j].max()/o[0]-1)>0.005 and c[j]<o[j]]
    ents["pullback"]=pb[:1]
    for k,idx in ents.items():
        for e in idx:
            if e>=len(c)-6: continue
            stop=c[e]-2.0*(h[e]-l[e])
            r=exits(o,h,l,c,e,stop)
            if r: rows.append(dict(entry=k,f3=r[0],tr=r[1],sym=s,date=dt))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} trades, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e10b_entries.parquet",index=False)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")
print(f"{'entry':16s}{'n':>9s}{'3R win':>9s}{'3R mean':>10s}{'t':>7s}{'trail win':>11s}{'trail mean':>12s}{'t':>7s}")
print("-"*82)
for k in ("random","level retest","ORB","VWAP reclaim","pullback"):
    x=T[T.entry==k]
    if len(x)<200: continue
    a,b=x.f3.values,x.tr.values
    print(f"{k:16s}{len(x):9,}{(a>0).mean():9.1%}{a.mean():+10.3f}"
          f"{a.mean()/(a.std()/np.sqrt(len(a))):+7.2f}"
          f"{(b>0).mean():11.1%}{b.mean():+12.3f}{b.mean()/(b.std()/np.sqrt(len(b))):+7.2f}")
print("\nfriction here is ~-0.017R, vs -0.135R in E10.  Any remaining spread is signal.")
