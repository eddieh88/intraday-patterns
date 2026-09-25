"""Where does the universal -0.1R come from?  Decompose it.

Same entries throughout (random bar, 09:30-11:00, top 100 names), varying only:
  (a) idealised fills, zero cost        -> pure signal + bracket geometry
  (b) idealised fills, 2bp              -> add costs
  (c) gap-through fills, zero cost      -> add slippage
  (d) gap-through fills, 2bp            -> what every experiment reported
and for three stop widths, since cost-as-a-fraction-of-R depends on the stop.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames
rng=np.random.default_rng(0); MAXB=60

def sim(o,h,l,c,e,stop,gap,cost_bp):
    entry=c[e]; risk=entry-stop
    if risk<=0 or risk/entry<0.0003: return None
    tgt=entry+3*risk; cost=cost_bp*1e-4*entry
    end=min(len(c),e+1+MAXB)
    for j in range(e+1,end):
        if l[j]<=stop: return ((min(stop,o[j]) if gap else stop)-entry-cost)/risk
        if h[j]>=tgt:  return ((max(tgt,o[j]) if gap else tgt)-entry-cost)/risk
    return (c[end-1]-entry-cost)/risk

files=sorted(glob.glob("cache/mp5min/*.parquet"))[::3]     # every 3rd session
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<40: continue
    o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
    hh=rth.h.values
    win=np.flatnonzero((hh>=9.5)&(hh<11.0))
    if not len(win): continue
    e=int(rng.choice(win))
    if e>=len(c)-8: continue
    bar=h[e]-l[e]
    for wlab,mult in (("0.5 bar",0.5),("1 bar",1.0),("2 bars",2.0)):
        stop=c[e]-mult*bar
        r={}
        for flab,gap in (("ideal",False),("gap",True)):
            for clab,cb in (("0bp",0.0),("2bp",2.0)):
                v=sim(o,h,l,c,e,stop,gap,cb)
                if v is None: r=None; break
                r[f"{flab}/{clab}"]=v
            if r is None: break
        if r: rows.append({**r,"width":wlab,"risk":(c[e]-stop)/c[e]})
    if i%20000==0 and i: print(f"  {i:,} sessions, {len(rows):,}, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows)
print(f"\n{len(T):,} simulated trades  ({time.time()-t0:.0f}s)\n")
print(f"{'stop width':12s}{'risk%':>8s}{'ideal/0bp':>12s}{'ideal/2bp':>12s}{'gap/0bp':>11s}{'gap/2bp':>11s}")
print("-"*68)
for w,g_ in T.groupby("width",sort=False):
    print(f"{w:12s}{g_.risk.median():8.2%}"
          f"{g_['ideal/0bp'].mean():+12.3f}{g_['ideal/2bp'].mean():+12.3f}"
          f"{g_['gap/0bp'].mean():+11.3f}{g_['gap/2bp'].mean():+11.3f}")
print("\ncolumn 1 is the GROSS result -- no costs, no slippage, perfect fills.")
print("If it is ~0, the market is efficient and everything after is friction.")
print("If it is clearly negative, the BRACKET ITSELF loses and that is the bug.")
