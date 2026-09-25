"""E10e: the symmetric entry test, with two errors fixed.

ERROR A -- read the wrong column.  With edge e and drift d:
    long  ~ e + d
    short ~ e - d
    L - S ~ 2d        cancels the EDGE, measures the DRIFT
   (L + S)/2 ~ e      cancels the DRIFT, measures the EDGE
E10c/E10d reported L-S as the edge statistic.  It is the drift statistic.
The mean of the two sides is the edge statistic.

ERROR B -- the universe was not point-in-time.  It ranked names on dollar
volume summed over the WHOLE 2021-2026 period, which selects the names that
became heavily traded because they ran.  Now: trailing 20-session dollar
volume, known before each session.

Also: standard errors clustered by session date, with the intraclass
correlation estimated from the data rather than assumed.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames
COST_BP, MAXB = 1.0, 60
rng=np.random.default_rng(0)

def trade(o,h,l,c,e,up):
    entry=c[e]; bar=h[e]-l[e]
    stop=entry-2*bar if up else entry+2*bar
    risk=abs(entry-stop)
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

# ---- point-in-time universe: trailing 20-session dollar volume ----
D=pd.read_parquet("cache/intraday_daily.parquet").sort_values(["symbol","date"])
D["dv"]=D.c_rth*D.v_rth
D["dv20"]=D.groupby("symbol").dv.transform(lambda x: x.shift(1).rolling(20,min_periods=10).mean())
D=D.dropna(subset=["dv20"])
D["rk"]=D.groupby("date").dv20.rank(ascending=False,method="first")
PIT={}                                  # date -> set of symbols eligible THAT day
for r in D[D.rk<=100].itertuples(): PIT.setdefault(r.date,set()).add(r.symbol)
allnames=set().union(*PIT.values())
print(f"point-in-time universe: {len(allnames):,} distinct names across "
      f"{len(PIT):,} sessions (vs 100 fixed before)",flush=True)

files=sorted(glob.glob("cache/mp5min/*.parquet"))
rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,allnames)):
    if dt not in PIT or s not in PIT[dt]: continue      # eligible that day only
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
    ent={("random",True):[int(rng.choice(win))],("random",False):[int(rng.choice(win))]}
    for up,lvl in ((True,pmh),(False,pml)):
        brk=None
        for j in win:
            if (up and c[j]>lvl) or ((not up) and c[j]<lvl): brk=int(j); break
        if brk is None: continue
        for r_ in range(brk+3,min(brk+16,len(c))):
            adv=(h[brk+1:r_].max()-lvl)/lvl if up else (lvl-l[brk+1:r_].min())/lvl
            if r_>brk+1 and adv<0.0018: continue
            if (up and l[r_]<=lvl and c[r_]>lvl) or ((not up) and h[r_]>=lvl and c[r_]<lvl):
                ent[("level",up)]=[r_]; break
    ent[("ORB",True)]=[int(j) for j in win if hh[j]>=10 and c[j]>orh][:1]
    ent[("ORB",False)]=[int(j) for j in win if hh[j]>=10 and c[j]<orl][:1]
    ent[("VWAP",True)]=[int(j) for j in win if j>2 and c[j-1]<vwap[j-1] and c[j]>vwap[j]][:1]
    ent[("VWAP",False)]=[int(j) for j in win if j>2 and c[j-1]>vwap[j-1] and c[j]<vwap[j]][:1]
    ent[("pullback",True)]=[int(j) for j in win if j>3 and (h[:j].max()/o[0]-1)>0.005 and c[j]<o[j]][:1]
    ent[("pullback",False)]=[int(j) for j in win if j>3 and (1-l[:j].min()/o[0])>0.005 and c[j]>o[j]][:1]
    for (k,up),idx in ent.items():
        for e in idx:
            if e>=len(c)-8: continue
            r_=trade(o,h,l,c,e,up)
            if r_ is not None: rows.append(dict(date=dt,entry=k,up=up,R=r_))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} trades, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e10e_corrected.parquet",index=False)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")

def clustered(x, by):
    """mean and t-stat with SEs clustered on date; also returns the ICC"""
    df=pd.DataFrame({"x":x,"g":by})
    gm=df.groupby("g").x.mean(); gn=df.groupby("g").x.size()
    m=x.mean(); k=len(gm)
    se=gm.std(ddof=1)/np.sqrt(k)                       # session-level SE
    mb=gn.mean()
    vb=gm.var(ddof=1); vw=df.groupby("g").x.var(ddof=1).mean()
    icc=vb/(vb+vw) if (vb+vw)>0 else np.nan
    return m, m/se if se>0 else np.nan, se, k, icc

print(f"{'entry':12s}{'long R':>9s}{'short R':>9s}{'(L+S)/2 = EDGE':>17s}{'clust t':>9s}"
      f"{'L-S = DRIFT':>14s}")
print("-"*72)
res={}
for k,g_ in T.groupby("entry"):
    L=g_[g_.up]; S=g_[~g_.up]
    if len(L)<200 or len(S)<200: continue
    avg=g_.copy(); avg["x"]=np.where(avg.up, avg.R, avg.R)   # both sides are already P&L
    m,t,se,nd,icc=clustered(avg.R.values, avg.date.values)
    res[k]=(m,se,nd,icc)
    print(f"{k:12s}{L.R.mean():+9.3f}{S.R.mean():+9.3f}{m:+17.4f}{t:+9.2f}"
          f"{L.R.mean()-S.R.mean():+14.3f}")
print("-"*72)
if "random" in res:
    rm,rse,rnd,ricc=res["random"]
    print(f"\nestimated intraclass correlation (random arm): {ricc:.4f}")
    print(f"sessions used as clusters: {rnd:,}\n")
    print(f"{'entry':12s}{'edge':>10s}{'excess over random':>20s}{'SE(diff)':>10s}{'t':>8s}")
    print("-"*62)
    for k,(m,se,nd,icc) in sorted(res.items(),key=lambda x:-x[1][0]):
        if k=="random": continue
        d=m-rm; sed=np.sqrt(se**2+rse**2)
        print(f"{k:12s}{m:+10.4f}{d:+20.4f}{sed:10.4f}{d/sed:+8.2f}")
    print(f"\n{'random':12s}{rm:+10.4f}{'(baseline)':>20s}")
    print(f"\nminimum detectable edge at 80% power, 5% two-sided: "
          f"~{2.8*np.sqrt(2)*rse:.4f}R")
