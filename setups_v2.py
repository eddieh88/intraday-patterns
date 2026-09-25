"""Horizontal-level breaks and TRENDLINE breaks, analysed separately.

Two corrections over the first version.

(1) A descending-trendline break is not the same event as a horizontal-level
    break.  The first joins falling swing highs and is broken when price stops
    making lower highs; the second is a price repeatedly rejected at one level.
    Pooling them measures neither.  Here they are detected and reported apart.

(2) Stops go below recent STRUCTURE, not below the entry bar.  Placing a stop
    at the entry bar's low put 17-34% of them inside 0.5% -- tighter than daily
    noise -- which turned routine gaps into double-digit R multiples.  Now the
    stop sits below the most recent confirmed swing LOW before entry, which is
    where a trader would actually put it.

LOOK-AHEAD: a pivot at bar i needs the K bars after it, so at decision bar b
only pivots with i <= b-K-1 are visible.  Enforced everywhere.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")

K, LOOKBACK, CLUST, MIN_SWINGS = 3, 60, 0.015, 3
BUF, RWIN, MAXBARS, PAD = 0.005, 15, 20, 0.002
# A retest is not the next day's dip.  Rendering real detections showed 73% of
# entries came one bar after the breakout: price closed above the level and
# pulled back the following morning.  That is a different event from the one in
# every diagram -- break, ADVANCE, return to the level days later, bounce.
MIN_GAP = 3        # bars between the breakout bar and the retest bar
MIN_ADV = 0.02     # price must first run this far above the level
TL_MIN_PTS, TL_MAX_SLOPE = 3, -1e-5      # descending trendline

def pivots(x, K, kind):
    n=len(x); out=np.zeros(n,bool)
    for i in range(K,n-K):
        w=x[i-K:i+K+1]
        if not np.isfinite(w).all(): continue
        if kind=="high" and x[i]==w.max() and (w[:K]<x[i]).all(): out[i]=True
        if kind=="low"  and x[i]==w.min() and (w[:K]>x[i]).all(): out[i]=True
    return out

def horiz_level(b, ph, h):
    """cluster confirmed pivot highs into a horizontal level"""
    u=ph[(ph<=b-K-1)&(ph>=b-LOOKBACK)]
    if len(u)<MIN_SWINGS: return None
    p=np.sort(h[u]); best=None
    for i in range(len(p)):
        g=p[(p>=p[i])&(p<=p[i]*(1+CLUST))]
        if len(g)>=MIN_SWINGS and (best is None or len(g)>best[1]): best=(g.mean(),len(g))
    return None if best is None else best[0]

def trendline(b, ph, h):
    """fit a DESCENDING line through the last TL_MIN_PTS confirmed pivot highs.
    returns its value at bar b, or None."""
    u=ph[(ph<=b-K-1)&(ph>=b-LOOKBACK)]
    if len(u)<TL_MIN_PTS: return None
    u=u[-TL_MIN_PTS:]
    s,i0=np.polyfit(u.astype(float), h[u], 1)
    if s>TL_MAX_SLOPE: return None                      # must slope DOWN
    # the line must not have been decisively breached between its anchors
    seg=np.arange(u[0],b)
    if (h[seg] > (s*seg+i0)*(1+BUF)).sum() > 1: return None
    return s*b+i0

def struct_stop(e, pl, l):
    """most recent CONFIRMED swing low before entry -- where a stop belongs"""
    u=pl[(pl<=e-K-1)&(pl>=e-LOOKBACK)]
    if len(u)==0: return None
    return l[u[-1]]*(1-PAD)

def scan(g):
    o,h,l,c=(g[k].values.astype(float) for k in ("open","high","low","close"))
    bad=g.bad_day.values; n=len(c)
    if n<LOOKBACK+RWIN+MAXBARS+2*K+2: return []
    ph=np.flatnonzero(pivots(h,K,"high")); pl=np.flatnonzero(pivots(l,K,"low"))
    out=[]
    for b in range(LOOKBACK, n-MAXBARS-1):
        if bad[max(0,b-LOOKBACK):b+MAXBARS+1].any(): continue
        # --- horizontal level break ---
        R=horiz_level(b,ph,h)
        if R is not None and np.isfinite(R) and R>0:
            if c[b-1]<=R*(1+BUF)<c[b]:
                out.append(("H_immediate",b,pl))
                for r in range(b+MIN_GAP,min(b+1+RWIN,n-MAXBARS)):
                    if h[b+1:r].size and (h[b+1:r].max()-R)/R < MIN_ADV: continue  # must advance first
                    if l[r]<=R*(1+CLUST/2):
                        k="H_bounce" if c[r]>R else ("H_failure" if c[r]<R*(1-CLUST/2) else None)
                        if k: out.append((k,r,pl))
                        break
            elif h[b]>=R*(1-CLUST/2) and c[b]<=R*(1+BUF) and h[b-1]<R*(1-CLUST/2):
                out.append(("H_no_breakout",b,pl))
        # --- descending trendline break ---
        T=trendline(b,ph,h)
        if T is not None and np.isfinite(T) and T>0:
            if c[b-1]<=T*(1+BUF)<c[b]:
                out.append(("T_immediate",b,pl))
                Rz=horiz_level(b,ph,h)                  # retest zone = horizontal pivots
                lvl=Rz if (Rz is not None and np.isfinite(Rz) and Rz>0) else T
                for r in range(b+MIN_GAP,min(b+1+RWIN,n-MAXBARS)):
                    if h[b+1:r].size and (h[b+1:r].max()-lvl)/lvl < MIN_ADV: continue
                    if l[r]<=lvl*(1+CLUST/2):
                        k="T_bounce" if c[r]>lvl else ("T_failure" if c[r]<lvl*(1-CLUST/2) else None)
                        if k: out.append((k,r,pl))
                        break
    return out

def bracket(o,h,l,c,e,stop,rr,realistic=True,cost_bp=10):
    entry=c[e]; risk=entry-stop
    if not np.isfinite(risk) or risk<=0 or risk/entry<0.002: return None
    target=entry+rr*risk; cost=(cost_bp*1e-4)*entry*2
    for i in range(e+1,min(e+1+MAXBARS,len(c))):
        if l[i]<=stop:  return (min(stop,o[i])-entry-cost)/risk
        if h[i]>=target: return (max(target,o[i])-entry-cost)/risk
    j=min(e+MAXBARS,len(c)-1)
    return (c[j]-entry-cost)/risk

if __name__=="__main__":
    import sys
    RR=float(sys.argv[1]) if len(sys.argv)>1 else 3.0
    df=pd.read_parquet("colab/colab_ohlcv.parquet").sort_values(["symbol","timestamp"])
    piv=df.pivot_table(index="timestamp",columns="symbol",values="close")
    B={}; RISK={}
    for j,(s,g) in enumerate(df.groupby("symbol",sort=False)):
        o,h,l,c=(g[k].values.astype(float) for k in ("open","high","low","close"))
        pl_arr=np.flatnonzero(pivots(l,K,"low"))
        for kind,e,_ in scan(g):
            st=struct_stop(e,pl_arr,l)
            if st is None: continue
            r=bracket(o,h,l,c,e,st,RR)
            if r is None: continue
            B.setdefault(kind,[]).append(r)
            RISK.setdefault(kind,[]).append((c[e]-st)/c[e])
        if j%150==0: print(f"  {j} names",flush=True)
    print(f"\nRR={RR:.0f}, structural stop below last swing low, gap fills, 10bp")
    print(f"{'setup':16s}{'n':>8s}{'stop%':>8s}{'win':>8s}{'exp(R)':>9s}{'median':>9s}{'t':>8s}")
    print("-"*70)
    for k in sorted(B):
        x=np.array(B[k]); rk=np.array(RISK[k])
        if len(x)<50: continue
        se=x.std()/np.sqrt(len(x))
        print(f"{k:16s}{len(x):8,}{np.median(rk):8.2%}{(x>0).mean():8.1%}"
              f"{x.mean():+9.3f}{np.median(x):+9.3f}{x.mean()/se:+8.2f}")
    for a,b_ in (("H_bounce","H_no_breakout"),("T_bounce","H_bounce"),("T_bounce","T_immediate")):
        if a in B and b_ in B:
            xa,xb=np.array(B[a]),np.array(B[b_])
            d=xa.mean()-xb.mean(); sed=np.sqrt(xa.var()/len(xa)+xb.var()/len(xb))
            print(f"\n{a} - {b_} = {d:+.3f}R  t = {d/sed:+.2f}")
