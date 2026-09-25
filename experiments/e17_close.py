"""E17: the three tests that close this out.

1. TIMING vs DIRECTION.  The after-only matched placebo inherits the signal's
   side, so the paired difference holds direction fixed: it asks whether
   entering AT the signal beats entering a few bars later.  The DIRECTION
   question needs the signal's ABSOLUTE gross R, since a random-side entry has
   zero expected gross R.  Both reported, for all four entries.

2. STOP-FIRST vs TARGET-FIRST.  When one bar spans both barriers we have always
   assumed the stop.  That washes out of differences but not out of LEVELS, and
   the direction test depends on levels.  Run both as bounds.

3. SELECTION.  The relvol result was side-balanced on a thin subsample, where
   that estimand's downward bias is largest.  Rerun with matched placebos.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, "lib")
from intraday_levels import session_frames
COST_BP, MAXB, K, CAP = 0.0, 60, 12, 3      # GROSS; cap signals per side/session
rng=np.random.default_rng(0)

def trade(o,h,l,c,e,up,risk,stop_first):
    entry=c[e]
    if risk<=0 or risk/entry<0.0003: return None
    stop=entry-risk if up else entry+risk
    tgt=entry+3*risk if up else entry-3*risk
    cost=COST_BP*1e-4*entry; end=min(len(c),e+1+MAXB)
    for j in range(e+1,end):
        hs = (l[j]<=stop) if up else (h[j]>=stop)
        ht = (h[j]>=tgt)  if up else (l[j]<=tgt)
        if hs and ht:                                    # bar spans both
            first_stop = stop_first
        elif hs: first_stop=True
        elif ht: first_stop=False
        else: continue
        if first_stop:
            return ((min(stop,o[j])-entry) if up else (entry-max(stop,o[j])) - 0)/risk - cost/risk
        return ((max(tgt,o[j])-entry) if up else (entry-min(tgt,o[j])) - 0)/risk - cost/risk
    return (((c[end-1]-entry) if up else (entry-c[end-1]))-cost)/risk

D=pd.read_parquet("cache/intraday_daily.parquet").sort_values(["symbol","date"])
D["dv"]=D.c_rth*D.v_rth
D["dv20"]=D.groupby("symbol").dv.transform(lambda x:x.shift(1).rolling(20,min_periods=10).mean())
D["orv14"]=D.groupby("symbol").v_or.transform(lambda x:x.shift(1).rolling(14,min_periods=7).mean())
D=D.dropna(subset=["dv20","orv14"])
D["relvol"]=D.v_or/D.orv14
# Universe from ONE place: data/build_daily.py's point-in-time pool, top 100 per day.
P=pd.read_parquet("cache/intraday_pool.parquet")
P=P[P.rk<=100].merge(D[["symbol","date","relvol"]], on=["symbol","date"], how="inner")
PIT={}; RV={}
for r in P.itertuples():
    PIT.setdefault(pd.Timestamp(r.date),set()).add(r.symbol); RV[(r.symbol,pd.Timestamp(r.date))]=r.relvol
allnames=set().union(*PIT.values())
files=sorted(glob.glob("cache/mp5min/*.parquet"))[::2]
print(f"{len(allnames)} names, {len(files)} sessions (every 2nd)",flush=True)

rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,allnames)):
    if dt not in PIT or s not in PIT[dt]: continue
    pre=g[g.h<9.5]; rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    if len(rth)<40 or len(pre)<5: continue
    o,h,l,c,v=(rth[k].values.astype(float) for k in ("open","high","low","close","volume"))
    hh=rth.h.values
    vwap=np.cumsum(((h+l+c)/3)*v)/np.maximum(np.cumsum(v),1)
    win=np.flatnonzero((hh>=9.5)&(hh<11.5))
    if len(win)<6: continue
    pmh,pml=pre.high.max(),pre.low.min()
    orh=h[hh<10].max() if (hh<10).any() else np.nan
    orl=l[hh<10].min() if (hh<10).any() else np.nan
    sig={}
    for up,lvl in ((True,pmh),(False,pml)):
        brk=None
        for j in win:
            if (up and c[j]>lvl) or ((not up) and c[j]<lvl): brk=int(j); break
        if brk is None: continue
        for r_ in range(brk+3,min(brk+16,len(c))):
            adv=(h[brk+1:r_].max()-lvl)/lvl if up else (lvl-l[brk+1:r_].min())/lvl
            if r_>brk+1 and adv<0.0018: continue
            if (up and l[r_]<=lvl and c[r_]>lvl) or ((not up) and h[r_]>=lvl and c[r_]<lvl):
                sig[("level",up)]=[r_]; break
    sig[("ORB",True)]=[int(j) for j in win if hh[j]>=10 and c[j]>orh][:1]
    sig[("ORB",False)]=[int(j) for j in win if hh[j]>=10 and c[j]<orl][:1]
    sig[("VWAP",True)]=[int(j) for j in win if j>2 and c[j-1]<vwap[j-1] and c[j]>vwap[j]][:CAP]
    sig[("VWAP",False)]=[int(j) for j in win if j>2 and c[j-1]>vwap[j-1] and c[j]<vwap[j]][:CAP]
    sig[("pullback",True)]=[int(j) for j in win if j>3 and (h[:j].max()/o[0]-1)>0.005 and c[j]<o[j]][:CAP]
    sig[("pullback",False)]=[int(j) for j in win if j>3 and (1-l[:j].min()/o[0])>0.005 and c[j]>o[j]][:CAP]
    rv=RV.get((s,dt),np.nan)
    for (k,up),idx in sig.items():
        for e in idx:
            if e>=len(c)-8: continue
            hi_=min(int(win[-1]),e+K,len(c)-9)
            cand=[x for x in range(e+1,hi_+1)]          # AFTER ONLY
            if not cand: continue
            p=int(rng.choice(cand)); rk=2*(h[e]-l[e])
            rec=dict(date=dt,entry=k,up=up,relvol=rv)
            ok=True
            for tag,sf in (("sf",True),("tf",False)):
                a=trade(o,h,l,c,e,up,rk,sf); b=trade(o,h,l,c,p,up,rk,sf)
                if a is None or b is None: ok=False; break
                rec[f"sig_{tag}"]=a; rec[f"pla_{tag}"]=b
            if ok: rows.append(rec)
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} pairs, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e17_close.parquet",index=False)
print(f"\n{len(T):,} matched pairs, GROSS  ({time.time()-t0:.0f}s)\n")
def cl(x,by):
    sm=pd.DataFrame({"x":x,"g":by}).groupby("g").x.mean()
    m=np.mean(x); se=sm.std(ddof=1)/np.sqrt(len(sm))
    return m,se,m/se
print("DIRECTION (signal absolute gross R; random side has zero expectation)")
print(f"{'entry':10s}{'stop-first':>26s}{'target-first':>26s}")
print(f"{'':10s}{'R':>10s}{'t':>7s}{'95% CI':>9s}{'R':>10s}{'t':>7s}{'95% CI':>9s}")
print("-"*64)
for k,g_ in T.groupby("entry"):
    out=[]
    for tag in ("sf","tf"):
        m,se,t=cl(g_[f"sig_{tag}"].values,g_.date.values); out.append((m,t,se))
    print(f"{k:10s}{out[0][0]:+10.4f}{out[0][1]:+7.2f}{'':9s}{out[1][0]:+10.4f}{out[1][1]:+7.2f}")
print("\nTIMING (signal minus delayed same-side entry; direction held fixed)")
print(f"{'entry':10s}{'n':>9s}{'diff (sf)':>12s}{'t':>8s}{'diff (tf)':>12s}{'t':>8s}")
print("-"*62)
for k,g_ in T.groupby("entry"):
    a,ase,at=cl((g_.sig_sf-g_.pla_sf).values,g_.date.values)
    b,bse,bt=cl((g_.sig_tf-g_.pla_tf).values,g_.date.values)
    print(f"{k:10s}{len(g_):9,}{a:+12.4f}{at:+8.2f}{b:+12.4f}{bt:+8.2f}")
print("\nSELECTION (relvol split, matched placebo, stop-first)")
print(f"{'condition':18s}{'n':>9s}{'direction R':>13s}{'t':>8s}{'timing':>10s}{'t':>8s}")
print("-"*68)
for lo,hi,lab in ((0,1.5,"relvol < 1.5x"),(1.5,3,"relvol 1.5-3x"),(3,99,"relvol > 3x")):
    x=T[(T.relvol>=lo)&(T.relvol<hi)]
    if len(x)<300: continue
    m,se,t=cl(x.sig_sf.values,x.date.values)
    d,dse,dt_=cl((x.sig_sf-x.pla_sf).values,x.date.values)
    print(f"{lab:18s}{len(x):9,}{m:+13.4f}{t:+8.2f}{d:+10.4f}{dt_:+8.2f}")
