"""E8: does the EXIT rule decide it?  Same entries, seven exit policies.

E6 used one exit -- 3R target or stop -- and found only 15.4% reached the
target while 13.2% ran out of time averaging +1.84R.  That is an exit problem,
not necessarily a signal problem.  Nobody trades a naked 3R bracket.

Same entries throughout, so any difference is purely the exit:
  1. fixed 3R
  2. fixed 2R
  3. fixed 1R
  4. breakeven stop after +1R, then 3R target
  5. trailing stop at 1 x ATR(14 bars)
  6. half off at +1R, remainder trailing 1 ATR
  7. time exit at 12:00
All exit at the 16:00 close if nothing else triggers.  2bp round trip.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames, find_setups
COST_BP=2.0

def run_exits(o,h,l,c,hh,e,stop0):
    """-> dict of policy -> R multiple"""
    entry=c[e]; risk=entry-stop0
    if risk<=0: return None
    cost=COST_BP*1e-4*entry
    pc=np.concatenate([[c[0]],c[:-1]])
    atr=pd.Series(np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))).rolling(14,min_periods=5).mean().values
    R=lambda p:(p-entry-cost)/risk
    out={}
    for name,rr in (("fixed 3R",3.0),("fixed 2R",2.0),("fixed 1R",1.0)):
        tgt=entry+rr*risk; res=None
        for j in range(e+1,len(c)):
            if l[j]<=stop0: res=R(min(stop0,o[j])); break
            if h[j]>=tgt:   res=R(max(tgt,o[j]));   break
        out[name]=res if res is not None else R(c[-1])
    # breakeven after +1R, then 3R
    st=stop0; tgt=entry+3*risk; res=None
    for j in range(e+1,len(c)):
        if l[j]<=st: res=R(min(st,o[j])); break
        if h[j]>=tgt: res=R(max(tgt,o[j])); break
        if h[j]>=entry+risk: st=max(st,entry)
    out["BE after 1R"]=res if res is not None else R(c[-1])
    # trailing 1 ATR
    st=stop0; res=None
    for j in range(e+1,len(c)):
        if l[j]<=st: res=R(min(st,o[j])); break
        a=atr[j] if np.isfinite(atr[j]) else (h[j]-l[j])
        st=max(st,h[j]-a)
    out["trail 1 ATR"]=res if res is not None else R(c[-1])
    # half at 1R, rest trailing
    st=stop0; half=None; res=None
    for j in range(e+1,len(c)):
        if l[j]<=st:
            r2=R(min(st,o[j])); res=(0.5*half+0.5*r2) if half is not None else r2; break
        if half is None and h[j]>=entry+risk:
            half=R(entry+risk); st=max(st,entry)
        a=atr[j] if np.isfinite(atr[j]) else (h[j]-l[j])
        if half is not None: st=max(st,h[j]-a)
    if res is None:
        r2=R(c[-1]); res=(0.5*half+0.5*r2) if half is not None else r2
    out["half 1R + trail"]=res
    # time exit at 12:00
    res=None
    for j in range(e+1,len(c)):
        if l[j]<=stop0: res=R(min(stop0,o[j])); break
        if hh[j]>=12.0: res=R(c[j]); break
    out["exit 12:00"]=res if res is not None else R(c[-1])
    return out

files=sorted(glob.glob("cache/mp5min/*.parquet"))
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
D=D[D.symbol.isin(NAMES)]
prior={(r.symbol,r.date):(r.pdh,r.pdl,r.pdc) for r in D.itertuples()}
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    if (s,dt) not in prior: continue
    pdh,pdl,pdc=prior[(s,dt)]; pre=g[g.h<9.5]
    ev=find_setups(g,{"PDH":pdh,"PDC":pdc,"ONH":pre.high.max() if len(pre) else None})
    if not ev: continue
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
    hh=rth.h.values
    for e in ev:
        if e["kind"]!="bounce": continue
        r=e["entry"]; stop0=e["R"]-0.5*(h[r]-l[r])      # just below the level
        res=run_exits(o,h,l,c,hh,r,stop0)
        if res: rows.append({**res,"sym":s,"date":dt,"level":e["level"]})
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} trades, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e8_exits.parquet",index=False)
POL=["fixed 1R","fixed 2R","fixed 3R","BE after 1R","trail 1 ATR","half 1R + trail","exit 12:00"]
print(f"\n{len(T):,} trades, identical entries, seven exits  ({time.time()-t0:.0f}s)\n")
print(f"{'exit policy':20s}{'win':>8s}{'mean R':>10s}{'median':>9s}{'t':>8s}{'best/worst':>14s}")
print("-"*70)
for p in POL:
    x=T[p].dropna().values; se=x.std()/np.sqrt(len(x))
    print(f"{p:20s}{(x>0).mean():8.1%}{x.mean():+10.3f}{np.median(x):+9.3f}{x.mean()/se:+8.2f}"
          f"{x.max():+7.1f}/{x.min():+.1f}")
