"""How often does the resolving bar contain BOTH the stop and the target?"""
import pandas as pd, numpy as np, glob, sys
sys.path.insert(0, ".")
from intraday_levels import session_frames
MAXB=60
def probe(o,h,l,c,e,up,risk):
    entry=c[e]
    if risk<=0 or risk/entry<0.0003: return None
    stop=entry-risk if up else entry+risk
    tgt=entry+3*risk if up else entry-3*risk
    for j in range(e+1,min(len(c),e+1+MAXB)):
        s = l[j]<=stop if up else h[j]>=stop
        t = h[j]>=tgt  if up else l[j]<=tgt
        if s or t: return (1 if (s and t) else 0, 1)
    return (0,0)            # no barrier hit -> time exit
D=pd.read_parquet("cache/intraday_daily.parquet").sort_values(["symbol","date"])
D["dv"]=D.c_rth*D.v_rth
D["dv20"]=D.groupby("symbol").dv.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean())
D=D.dropna(subset=["dv20"]); D["rk"]=D.groupby("date").dv20.rank(ascending=False,method="first")
PIT={}
for r in D[D.rk<=100].itertuples(): PIT.setdefault(r.date,set()).add(r.symbol)
n=both=barrier=0
for s,dt,g in session_frames(sorted(glob.glob("cache/mp5min/*.parquet"))[::4],set().union(*PIT.values())):
    if dt not in PIT or s not in PIT[dt]: continue
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<40: continue
    o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
    hh=rth.h.values; win=np.flatnonzero((hh>=9.5)&(hh<11.5))
    if len(win)<6: continue
    for e in win[:-8]:
        e=int(e)
        for up in (True,False):
            r=probe(o,h,l,c,e,up,2*(h[e]-l[e]))
            if r: n+=1; both+=r[0]; barrier+=r[1]
print(f"{n:,} entries   {barrier:,} resolved at a barrier ({barrier/n:.1%})")
print(f"{both:,} of those had ONE bar containing both stop and target = {both/barrier:.2%} of resolved, {both/n:.2%} of all")
