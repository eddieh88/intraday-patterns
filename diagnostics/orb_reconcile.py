"""Isolate the ORB signal-R discrepancy: -0.0700 (diagnostic) vs +0.0198 (E18).
Toggle each difference between the two runs one at a time."""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames
MAXB=60
def trade(o,h,l,c,e,up,risk,cost_bp):
    entry=c[e]
    if risk<=0 or risk/entry<0.0003: return None
    stop=entry-risk if up else entry+risk
    tgt=entry+3*risk if up else entry-3*risk
    cost=cost_bp*1e-4*entry; end=min(len(c),e+1+MAXB)
    for j in range(e+1,end):
        if up:
            if l[j]<=stop: return (min(stop,o[j])-entry-cost)/risk
            if h[j]>=tgt:  return (max(tgt,o[j])-entry-cost)/risk
        else:
            if h[j]>=stop: return (entry-max(stop,o[j])-cost)/risk
            if l[j]<=tgt:  return (entry-min(tgt,o[j])-cost)/risk
    return (((c[end-1]-entry) if up else (entry-c[end-1]))-cost)/risk
D=pd.read_parquet("cache/intraday_daily.parquet").sort_values(["symbol","date"])
D["dv"]=D.c_rth*D.v_rth
D["dv20"]=D.groupby("symbol").dv.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean())
D=D.dropna(subset=["dv20"]); D["rk"]=D.groupby("date").dv20.rank(ascending=False,method="first")
PIT={}
for r in D[D.rk<=100].itertuples(): PIT.setdefault(r.date,set()).add(r.symbol)
allnames=set().union(*PIT.values())
out={}
for stride,lab in ((10,"every 10th"),(2,"every 2nd")):
    files=sorted(glob.glob("cache/mp5min/*.parquet"))[::stride]
    rec=[]
    for s,dt,g in session_frames(files,allnames):
        if dt not in PIT or s not in PIT[dt]: continue
        rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
        if len(rth)<40: continue
        o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
        hh=rth.h.values; win=np.flatnonzero((hh>=9.5)&(hh<11.5))
        if len(win)<6: continue
        orh=h[hh<10].max() if (hh<10).any() else np.nan
        orl=l[hh<10].min() if (hh<10).any() else np.nan
        for up,cond in ((True,lambda j: np.isfinite(orh) and hh[j]>=10 and c[j]>orh),
                        (False,lambda j: np.isfinite(orl) and hh[j]>=10 and c[j]<orl)):
            for e in [int(j) for j in win if cond(j)][:1]:
                if e>=len(c)-8: continue
                rk=2*(h[e]-l[e])
                # does an AFTER-candidate exist?  the diagnostic required one
                hi_=min(int(win[-1]),e+12,len(c)-9)
                has_after = hi_>e
                for cb in (0.0,1.0):
                    v=trade(o,h,l,c,e,up,rk,cb)
                    if v is not None: rec.append((up,cb,v,has_after))
    R=pd.DataFrame(rec,columns=["up","cost","R","has_after"]); out[lab]=R
    print(f"{lab}: {len(R)//2:,} ORB signals",flush=True)
print(f"\n{'sample':12s}{'sides':10s}{'cost':>6s}{'after-cand':>12s}{'signal R':>11s}{'n':>9s}")
print("-"*62)
for lab,R in out.items():
    for sides,m in (("long only",R.up),("both",R.up|~R.up)):
        for cb in (0.0,1.0):
            for req,fl in (("all",R.has_after|~R.has_after),("required",R.has_after)):
                x=R[m&(R.cost==cb)&fl]
                if len(x)<50: continue
                print(f"{lab:12s}{sides:10s}{cb:6.0f}{req:>12s}{x.R.mean():+11.4f}{len(x):9,}")
