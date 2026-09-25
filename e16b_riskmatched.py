"""E16b: matched placebo, with the RISK UNIT matched too.

Every prior statistic weighted trades in a way that depends on n, the number of
signals per side that session, which is only known at 11:00:

  trade-weighted  over-weights the MAJORITY side, which is the side the day
                  rewarded  -> biased UP
  side-balanced   gives the MINORITY side equal weight; on a trend day that is
                  a handful of counter-trend signals that mostly lose
                  -> biased DOWN

Both are Simpson's-paradox artifacts.  Neither answers "does the entry pick
direction", and side-balancing is not even tradable -- you cannot size by 1/n
without knowing n in advance.

THE FIX: pair every signal with ITS OWN placebo -- a random bar within +/-K bars,
same name, same session, same side.  Average the signal-minus-placebo
differences with EQUAL WEIGHT PER TRADE, clustered by session.  The placebo
inherits the signal's side and timing, so tilt, time-of-day and cost geometry
all cancel, and no n-dependent weight appears anywhere.

E16 matched side, session and time neighbourhood but NOT the risk unit.  Each
arm took stop = 2 x ITS OWN bar range, so a breakout signal got a wide stop and
a distant 3R target while its quiet neighbour got a tight stop and a near one.
The placebo reached +3R 14.3% of the time against the signal's 5.6%, and the
paired difference measured bar width rather than entry quality.

Here the placebo inherits the SIGNAL's risk in price terms.  Only the entry
bar differs.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames
COST_BP, MAXB, K = 1.0, 60, 12          # placebo drawn within +/-12 bars (1 hour)
rng=np.random.default_rng(0)

def trade(o,h,l,c,e,up,risk=None):
    entry=c[e]
    if risk is None: risk=2*(h[e]-l[e])          # signal sets the risk unit
    stop=entry-risk if up else entry+risk
    if risk<=0 or risk/entry<0.0003: return None
    tgt=entry+3*risk if up else entry-3*risk
    cost=COST_BP*1e-4*entry; end=min(len(c),e+1+MAXB)
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
D=D.dropna(subset=["dv20"])
D["rk"]=D.groupby("date").dv20.rank(ascending=False,method="first")
PIT={}
for r in D[D.rk<=100].itertuples(): PIT.setdefault(r.date,set()).add(r.symbol)
allnames=set().union(*PIT.values())
print(f"{len(allnames)} names, {len(PIT):,} sessions",flush=True)

files=sorted(glob.glob("cache/mp5min/*.parquet")); rows=[]; t0=time.time()
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
                sig.setdefault(("level",up),[]).append(r_); break
    for up,cond in ((True,lambda j: hh[j]>=10 and c[j]>orh),(False,lambda j: hh[j]>=10 and c[j]<orl)):
        sig[("ORB",up)]=[int(j) for j in win if cond(j)][:1]
    for up,cond in ((True,lambda j: j>2 and c[j-1]<vwap[j-1] and c[j]>vwap[j]),
                    (False,lambda j: j>2 and c[j-1]>vwap[j-1] and c[j]<vwap[j])):
        sig[("VWAP",up)]=[int(j) for j in win if cond(j)]
    for up,cond in ((True,lambda j: j>3 and (h[:j].max()/o[0]-1)>0.005 and c[j]<o[j]),
                    (False,lambda j: j>3 and (1-l[:j].min()/o[0])>0.005 and c[j]>o[j])):
        sig[("pullback",up)]=[int(j) for j in win if cond(j)]
    for (k,up),idx in sig.items():
        for e in idx:
            if e>=len(c)-8: continue
            # MATCHED PLACEBO: random bar within +/-K of THIS signal, same side
            lo_,hi_=max(int(win[0]),e-K), min(int(win[-1]),e+K,len(c)-9)
            if hi_<=lo_: continue
            cand=[x for x in range(lo_,hi_+1) if x!=e]
            if not cand: continue
            p=int(rng.choice(cand))
            rk=2*(h[e]-l[e])                     # the SIGNAL's risk, in price
            a=trade(o,h,l,c,e,up,rk); b=trade(o,h,l,c,p,up,rk)   # placebo inherits it
            if a is None or b is None: continue
            rows.append(dict(date=dt,entry=k,up=up,sig=a,pla=b,diff=a-b))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} pairs, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e16b_riskmatched.parquet",index=False)
print(f"\n{len(T):,} matched pairs  ({time.time()-t0:.0f}s)\n")
print(f"{'entry':12s}{'n pairs':>9s}{'signal':>9s}{'placebo':>9s}{'diff':>9s}"
      f"{'clust t':>9s}{'95% CI':>22s}")
print("-"*80)
for k,g_ in T.groupby("entry"):
    if len(g_)<200: continue
    sm=g_.groupby("date")["diff"].mean()            # session means of the PAIRED difference
    m=g_["diff"].mean(); se=sm.std(ddof=1)/np.sqrt(len(sm))
    print(f"{k:12s}{len(g_):9,}{g_.sig.mean():+9.4f}{g_.pla.mean():+9.4f}{m:+9.4f}"
          f"{m/se:+9.2f}   [{m-1.96*se:+.4f}, {m+1.96*se:+.4f}]")
print("-"*80)
print("\nequal weight per trade, no n-dependent weighting anywhere.")
print("each placebo shares its signal's name, session, side and time neighbourhood.")
for k,g_ in T.groupby("entry"):
    if len(g_)<200: continue
    print(f"  {k:10s} gross edge in price terms: {g_['diff'].mean()*0.009*1e4:+.2f} bp")
