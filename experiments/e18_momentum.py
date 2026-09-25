"""E18: (a) reconcile the ORB discrepancy, (b) the momentum benchmark.

(a) RECONCILIATION -- HYPOTHESIS REFUTED BY THIS SCRIPT, DO NOT CITE IT.
    The hypothesis was that the diagnostic which found error 09 evaluated
    EVERY candidate placebo per signal, so signals with more candidates got
    more weight.  Part (a) below tests that and it is WRONG: the reweighting
    moves ORB by 0.005R and corr(n candidates, signal R) is -0.014.
    The real cause was found afterwards -- see diagnostics/orb_reconcile.py.
    The diagnostic traded LONG BREAKS ONLY, net of 1bp, on every 10th session.

(b) MOMENTUM BENCHMARK.  A positive direction R shows the entries pick the side
    that continues.  But the open has documented short-horizon continuation, so
    a rule that simply goes with the recent move might earn the same 1-2bp.
    Benchmark: same name, same bar, same stop geometry, side = sign of the past
    k bars' return.  If the setups do not beat that, the edge is generic
    continuation rather than anything specific to the pattern.

Also reports long and short direction R separately, since a zero benchmark
assumes the long/short mix does not pick up 2021-26 drift.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, "lib")
from intraday_levels import session_frames
COST_BP, MAXB, K, CAP = 0.0, 60, 12, 3
# FILL=close enters at the close of the bar that produced the signal -- the bar
# whose close the signal itself needs, so it is mildly optimistic. FILL=next
# enters at the following bar's open, which is tradeable.
#   python3 experiments/e18_momentum.py          # close
#   python3 experiments/e18_momentum.py next     # next-bar open
FILL = sys.argv[1] if len(sys.argv) > 1 else "close"
assert FILL in ("close", "next"), FILL
rng=np.random.default_rng(0)

def trade(o,h,l,c,e,up,risk):
    entry=c[e] if FILL=="close" else o[e+1]   # bar e+1 is then checked in full: its range
                                              # all happens after its open
    if risk<=0 or risk/entry<0.0003: return None
    stop=entry-risk if up else entry+risk
    tgt=entry+3*risk if up else entry-3*risk
    cost=COST_BP*1e-4*entry; end=min(len(c),e+1+MAXB)
    for j in range(e+1,end):
        if up:
            if l[j]<=stop: return (min(stop,o[j])-entry-cost)/risk
            if h[j]>=tgt:  return (max(tgt,o[j])-entry-cost)/risk
        else:
            if h[j]>=stop: return (entry-max(stop,o[j])-cost)/risk
            if l[j]<=tgt:  return (entry-min(tgt,o[j])-cost)/risk
    return (((c[end-1]-entry) if up else (entry-c[end-1]))-cost)/risk

# The point-in-time universe comes from ONE place: data/build_daily.py ranks every
# name on its prior 20 sessions of RTH dollar volume. Top 100 per day.
P=pd.read_parquet("cache/intraday_pool.parquet")
PIT={}
for r in P[P.rk<=100].itertuples(): PIT.setdefault(pd.Timestamp(r.date),set()).add(r.symbol)
allnames=set().union(*PIT.values())
files=sorted(glob.glob("cache/mp5min/*.parquet"))[::2]
print(f"{len(files)} sessions",flush=True)

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
    for (k,up),idx in sig.items():
        for e in idx:
            if e>=len(c)-8: continue
            rk=2*(h[e]-l[e]); a=trade(o,h,l,c,e,up,rk)
            if a is None: continue
            rec=dict(date=dt,entry=k,up=up,sig=a,ncand=max(0,min(int(win[-1]),e+K,len(c)-9)-e))
            for kk in (3,6,12):                   # momentum benchmark at the SAME bar
                if e-kk<0: rec[f"mom{kk}"]=np.nan; continue
                mu = c[e]>c[e-kk]                 # side = sign of past kk bars
                m=trade(o,h,l,c,e,mu,rk)
                rec[f"mom{kk}"]=m if m is not None else np.nan
            rows.append(rec)
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,}, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet(f"cache/e18_momentum_{FILL}.parquet",index=False)
def cl(x,by):
    x=np.asarray(x,float); m=np.nanmean(x)
    sm=pd.DataFrame({"x":x,"g":by}).dropna().groupby("g").x.mean()
    se=sm.std(ddof=1)/np.sqrt(len(sm)); return m,se,m/se
print(f"\n{len(T):,} signals, GROSS, fill={FILL}  ({time.time()-t0:.0f}s)\n")
print("(a) RECONCILIATION -- does candidate-count weighting explain the gap?")
o_=T[T.entry=="ORB"]
m,se,t=cl(o_.sig.values,o_.date.values)
w=np.average(o_.sig.values,weights=np.maximum(o_.ncand.values,1))
print(f"    equal weight per signal          {m:+.4f}")
print(f"    weighted by n candidate placebos {w:+.4f}   <- what the diagnostic did")
print(f"    corr(n candidates, signal R) = {np.corrcoef(o_.ncand,o_.sig)[0,1]:+.3f}")
print("\n(b) MOMENTUM BENCHMARK -- same bar, same stop, side = sign of past k bars")
print(f"{'entry':10s}{'signal':>9s}{'t':>7s}{'mom k=3':>10s}{'mom k=6':>10s}{'mom k=12':>10s}{'sig-mom6':>11s}{'t':>7s}")
print("-"*76)
for k,g_ in T.groupby("entry"):
    a,_,at=cl(g_.sig.values,g_.date.values)
    m3,_,_=cl(g_.mom3.values,g_.date.values); m6,_,_=cl(g_.mom6.values,g_.date.values)
    m12,_,_=cl(g_.mom12.values,g_.date.values)
    d,dse,dt_=cl((g_.sig-g_.mom6).values,g_.date.values)
    print(f"{k:10s}{a:+9.4f}{at:+7.2f}{m3:+10.4f}{m6:+10.4f}{m12:+10.4f}{d:+11.4f}{dt_:+7.2f}")
print("\n(c) LONG vs SHORT direction R (a zero benchmark assumes drift cancels)")
print(f"{'entry':10s}{'long':>10s}{'t':>7s}{'short':>10s}{'t':>7s}")
print("-"*46)
for k,g_ in T.groupby("entry"):
    L=g_[g_.up]; S=g_[~g_.up]
    a,_,at=cl(L.sig.values,L.date.values); b,_,bt=cl(S.sig.values,S.date.values)
    print(f"{k:10s}{a:+10.4f}{at:+7.2f}{b:+10.4f}{bt:+7.2f}")
