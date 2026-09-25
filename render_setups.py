"""Render real detected setups, so the detector can be checked by eye.

Every parameter in setups_v2.py is a judgement call, and a parameter sweep
cannot tell you whether the thing being detected is the thing a trader would
call a break-and-retest.  Only looking at the charts can.

    python3 render_setups.py            # 6 examples, mixed outcomes
    python3 render_setups.py T 3        # 3 trendline winners

Writes figures/real_setups.png
"""
import numpy as np, pandas as pd, warnings, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
warnings.filterwarnings("ignore"); sys.path.insert(0, ".")
from setups_v2 import (pivots, horiz_level, trendline, struct_stop,
                       K, LOOKBACK, CLUST, MIN_SWINGS, BUF, RWIN, MAXBARS, PAD, TL_MIN_PTS)
RR=3.0

df=pd.read_parquet("colab/colab_ohlcv.parquet").sort_values(["symbol","timestamp"])
EV=[]
for s,g in df.groupby("symbol",sort=False):
    o,h,l,c=(g[k].values.astype(float) for k in ("open","high","low","close"))
    t=g.timestamp.values; bad=g.bad_day.values; n=len(c)
    if n<LOOKBACK+RWIN+MAXBARS+2*K+2: continue
    ph=np.flatnonzero(pivots(h,K,"high")); pl=np.flatnonzero(pivots(l,K,"low"))
    for b in range(LOOKBACK,n-MAXBARS-1):
        if bad[max(0,b-LOOKBACK):b+MAXBARS+1].any(): continue
        R=horiz_level(b,ph,h)
        T=trendline(b,ph,h)
        for kind,lvl,brk in (("H",R,R),("T",T,None)):
            if lvl is None or not np.isfinite(lvl) or lvl<=0: continue
            if not (c[b-1]<=lvl*(1+BUF)<c[b]): continue
            zone = R if kind=="T" and R is not None and np.isfinite(R) and R>0 else lvl
            for r in range(b+1,min(b+1+RWIN,n-MAXBARS)):
                if l[r]<=zone*(1+CLUST/2):
                    if c[r]>zone:
                        st=struct_stop(r,pl,l)
                        if st is None: continue
                        risk=c[r]-st
                        if risk<=0 or risk/c[r]<0.002: continue
                        tgt=c[r]+RR*risk
                        out=0.0
                        for i in range(r+1,min(r+1+MAXBARS,n)):
                            if l[i]<=st: out=-1.0; break
                            if h[i]>=tgt: out=RR; break
                        else:
                            j=min(r+MAXBARS,n-1); out=(c[j]-c[r])/risk
                        EV.append(dict(sym=s,kind=kind,b=b,r=r,lvl=zone,tl=T,stop=st,
                                       tgt=tgt,out=out,o=o,h=h,l=l,c=c,t=t,ph=ph,pl=pl))
                    break
print(f"{len(EV):,} entries captured")
rng=np.random.default_rng(0)
def pick(kind, lo, hi, n=1):
    cand=[e for e in EV if e["kind"]==kind and lo<=e["out"]<=hi]
    return [cand[i] for i in rng.choice(len(cand), min(n,len(cand)), replace=False)] if cand else []

SEL = pick("T",2.9,3.1,2)+pick("T",-1.05,-0.95,1)+pick("H",2.9,3.1,2)+pick("H",-1.05,-0.95,1)
fig,ax=plt.subplots(2,3,figsize=(19,9))
for a,e in zip(ax.ravel(),SEL):
    b,r=e["b"],e["r"]; lo=max(0,b-45); hi=min(len(e["c"]),r+MAXBARS+3)
    x=np.arange(lo,hi); o,h,l,c=e["o"][lo:hi],e["h"][lo:hi],e["l"][lo:hi],e["c"][lo:hi]
    for i,(xx,oo,hh,ll,cc) in enumerate(zip(x,o,h,l,c)):
        col="#2ca02c" if cc>=oo else "#d62728"
        a.plot([xx,xx],[ll,hh],color=col,lw=.7)
        a.plot([xx,xx],[oo,cc],color=col,lw=2.6,solid_capstyle="butt")
    a.axhline(e["lvl"],color="#1f77b4",lw=1.6,label="S/R level")
    if e["kind"]=="T":
        u=e["ph"][(e["ph"]<=b-K-1)&(e["ph"]>=b-LOOKBACK)][-TL_MIN_PTS:]
        if len(u)>=2:
            s_,i0=np.polyfit(u.astype(float),e["h"][u],1)
            xs=np.arange(u[0],b+1); a.plot(xs,s_*xs+i0,"--",color="#7f7f7f",lw=1.3,label="trendline")
    a.axvline(b,color="#ff7f0e",lw=1.1,ls=":"); a.axvline(r,color="#111",lw=1.4)
    a.axhline(e["stop"],color="#d62728",lw=1.2,ls="--")
    a.axhline(e["tgt"],color="#2ca02c",lw=1.2,ls="--")
    a.axhspan(e["stop"],e["c"][r],color="#d62728",alpha=.09)
    a.axhspan(e["c"][r],e["tgt"],color="#2ca02c",alpha=.09)
    rr=(e["tgt"]-e["c"][r])/(e["c"][r]-e["stop"])
    a.set_title(f"{e['sym']}  {str(e['t'][r])[:10]}  {e['kind']}-bounce   "
                f"stop {(e['c'][r]-e['stop'])/e['c'][r]:.1%}  R:R {rr:.1f}  -> {e['out']:+.1f}R",fontsize=8)
    a.set_xticks([]); a.tick_params(labelsize=7)
    a.legend(fontsize=6,loc="upper left")
fig.suptitle("Real detected setups.  Orange dotted = breakout bar,  black = entry (retest bounce),  "
             "red band = risk,  green band = 3R target",fontsize=11)
plt.tight_layout(); import os
os.makedirs("figures", exist_ok=True)
OUT="figures/real_setups_v2.png"
plt.savefig(OUT,dpi=120,facecolor="white")
print("wrote",OUT)
