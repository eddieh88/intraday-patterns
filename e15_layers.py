"""E15: the layers above the pattern -- selection and execution.

The entry rule alone, applied unconditionally, does not pay (E10f, side-balanced:
every entry significantly worse than random).  Review argues any real edge lives
in selection, sizing and execution rather than in the pattern.  Two of those are
testable with what we have.

SELECTION.  Discretionary traders take 3-4 names a day that are "in play".  We
average over ~280,000 name-sessions.  Condition on in-play proxies known before
the entry: opening relative volume, and overnight gap size.

EXECUTION.  A passive fill at the level EARNS the half-spread instead of paying
it -- a swing of one full spread per trade, larger than any edge measured here.
This computes an upper bound: fill at the level rather than the signal-bar
close, with the cost sign flipped.  It is a bound, not a simulation: a resting
limit suffers adverse selection that OHLC bars cannot show.

Statistic throughout is the SIDE-BALANCED session-paired excess over random --
the corrected one.  Trade-weighting conflates signal tilt with edge.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames
MAXB=60

def trade(o,h,l,c,e,up,entry_px,cost_bp):
    """cost_bp > 0 pays the spread; cost_bp < 0 earns it (passive bound)"""
    entry=entry_px; bar=h[e]-l[e]
    stop=entry-2*bar if up else entry+2*bar
    risk=abs(entry-stop)
    if risk<=0 or risk/entry<0.0003: return None
    tgt=entry+3*risk if up else entry-3*risk
    cost=cost_bp*1e-4*entry; end=min(len(c),e+1+MAXB)
    for j in range(e+1,end):
        if up:
            if l[j]<=stop: return (min(stop,o[j])-entry-cost)/risk
            if h[j]>=tgt:  return (max(tgt,o[j])-entry-cost)/risk
        else:
            if h[j]>=stop: return (entry-max(stop,o[j])-cost)/risk
            if l[j]<=tgt:  return (entry-min(tgt,o[j])-cost)/risk
    return ((c[end-1]-entry) if up else (entry-c[end-1]))/risk - cost/risk

D=pd.read_parquet("cache/intraday_daily.parquet").sort_values(["symbol","date"])
D["dv"]=D.c_rth*D.v_rth
D["dv20"]=D.groupby("symbol").dv.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean())
D["orv14"]=D.groupby("symbol").v_or.transform(lambda x:x.shift(1).rolling(14,min_periods=7).mean())
D["pdc"]=D.groupby("symbol").c_rth.shift(1)
D=D.dropna(subset=["dv20","orv14","pdc"])
D["relvol"]=D.v_or/D.orv14
D["gap"]=(D.o_or/D.pdc-1).abs()
D["rk"]=D.groupby("date").dv20.rank(ascending=False,method="first")
PIT={}; CTX={}
for r in D[D.rk<=100].itertuples():
    PIT.setdefault(r.date,set()).add(r.symbol)
    CTX[(r.symbol,r.date)]=(r.relvol,r.gap)
allnames=set().union(*PIT.values())
print(f"{len(allnames)} names, {len(PIT):,} sessions",flush=True)

files=sorted(glob.glob("cache/mp5min/*.parquet"))
rng=np.random.default_rng(0); rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,allnames)):
    if dt not in PIT or s not in PIT[dt]: continue
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<40: continue
    o,h,l,c,v=(rth[k].values.astype(float) for k in ("open","high","low","close","volume"))
    hh=rth.h.values
    vwap=np.cumsum(((h+l+c)/3)*v)/np.maximum(np.cumsum(v),1)
    win=np.flatnonzero((hh>=9.5)&(hh<11.5))
    if len(win)<6: continue
    relvol,gap=CTX.get((s,dt),(np.nan,np.nan))
    ent={("random",True):[(int(rng.choice(win)),None)],
         ("random",False):[(int(rng.choice(win)),None)]}
    # VWAP reclaim: the passive price IS the vwap level at that bar
    ent[("VWAP",True)]=[(int(j),vwap[j]) for j in win if j>2 and c[j-1]<vwap[j-1] and c[j]>vwap[j]][:1]
    ent[("VWAP",False)]=[(int(j),vwap[j]) for j in win if j>2 and c[j-1]>vwap[j-1] and c[j]<vwap[j]][:1]
    for (k,up),lst in ent.items():
        for e,lvl in lst:
            if e>=len(c)-8: continue
            act=trade(o,h,l,c,e,up,c[e],1.0)                      # aggressive: pay 1bp at the close
            pas=trade(o,h,l,c,e,up,lvl if lvl else c[e],-1.0)     # passive bound: fill at level, earn 1bp
            if act is None or pas is None: continue
            rows.append(dict(date=dt,entry=k,up=up,R_act=act,R_pas=pas,relvol=relvol,gap=gap))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,}, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e15_layers.parquet",index=False)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")

def balanced(sub,k,col):
    a=sub[sub.entry==k].groupby(["date","up"])[col].mean().unstack().mean(axis=1)
    b=sub[sub.entry=="random"].groupby(["date","up"])[col].mean().unstack().mean(axis=1)
    d=(a-b).dropna()
    if len(d)<40: return None
    return d.mean(), d.std(ddof=1)/np.sqrt(len(d)), len(d)

print("EXECUTION -- VWAP reclaim, side-balanced excess over random")
print(f"{'fill assumption':34s}{'excess':>10s}{'t':>8s}{'sessions':>10s}")
print("-"*64)
for lab,col in (("aggressive, pay 1bp at close","R_act"),
                ("passive bound, earn 1bp at level","R_pas")):
    r=balanced(T,"VWAP",col)
    if r: print(f"{lab:34s}{r[0]:+10.4f}{r[0]/r[1]:+8.2f}{r[2]:10,}")

print("\nSELECTION -- passive-bound VWAP, conditioned on in-play proxies")
print(f"{'condition':30s}{'excess':>10s}{'t':>8s}{'sessions':>10s}")
print("-"*60)
for lo,hi,lab in ((0,1.5,"relvol < 1.5x"),(1.5,3,"relvol 1.5-3x"),(3,99,"relvol > 3x")):
    sub=T[(T.relvol>=lo)&(T.relvol<hi)]
    r=balanced(sub,"VWAP","R_pas")
    if r: print(f"{lab:30s}{r[0]:+10.4f}{r[0]/r[1]:+8.2f}{r[2]:10,}")
for lo,hi,lab in ((0,.005,"gap < 0.5%"),(.005,.02,"gap 0.5-2%"),(.02,9,"gap > 2%")):
    sub=T[(T.gap>=lo)&(T.gap<hi)]
    r=balanced(sub,"VWAP","R_pas")
    if r: print(f"{lab:30s}{r[0]:+10.4f}{r[0]/r[1]:+8.2f}{r[2]:10,}")
