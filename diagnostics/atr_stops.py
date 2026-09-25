"""Re-run with ATR-scaled stops.

A stop at the entry bar's low is inside the noise when that bar is narrow --
17-34% of setups ended up with stops under 0.5%, which turns routine gaps into
double-digit R multiples in both directions.  Real stops are placed relative to
volatility.  Here: stop is the FURTHER of (bar low - pad) and (entry - M*ATR14),
so it can never be closer than half an average day's range.
"""
import numpy as np, pandas as pd, warnings, sys
warnings.filterwarnings("ignore"); sys.path.insert(0, "lib")
from swing_levels import scan_trades
RR, MAXBARS, PAD, ATR_MULT, ATR_N = 3.0, 20, 0.002, 0.5, 14

def atr(h,l,c,n=ATR_N):
    pc=np.concatenate([[c[0]],c[:-1]])
    tr=np.maximum(h-l, np.maximum(np.abs(h-pc), np.abs(l-pc)))
    return pd.Series(tr).rolling(n).mean().values

def bracket(o,h,l,c,a,e,rr,realistic,cost_bp):
    entry=c[e]
    stop=min(l[e]*(1-PAD), entry-ATR_MULT*a[e]) if np.isfinite(a[e]) else l[e]*(1-PAD)
    risk=entry-stop
    if not np.isfinite(risk) or risk<=0: return None
    target=entry+rr*risk; cost=(cost_bp*1e-4)*entry*2
    for i in range(e+1,min(e+1+MAXBARS,len(c))):
        if l[i]<=stop:
            f=min(stop,o[i]) if realistic else stop
            return (f-entry-cost)/risk
        if h[i]>=target:
            f=max(target,o[i]) if realistic else target
            return (f-entry-cost)/risk
    j=min(e+MAXBARS,len(c)-1)
    return (c[j]-entry-cost)/risk

df=pd.read_parquet("colab/colab_ohlcv.parquet").sort_values(["symbol","timestamp"])
GR=list(df.groupby("symbol",sort=False))
def run(realistic,cost,rr=RR):
    B={k:[] for k in ("bounce","immediate","failure","no_breakout")}
    for s,g in GR:
        o,h,l,c=(g[k].values.astype(float) for k in ("open","high","low","close"))
        a=atr(h,l,c)
        for k,e in scan_trades(g):
            r=bracket(o,h,l,c,a,e,rr,realistic,cost)
            if r is not None: B[k].append(r)
    return {k:np.array(v) for k,v in B.items()}

for lab,real,cost in (("idealised fills, 0 cost",False,0),
                      ("gap fills, 0 cost",True,0),
                      ("gap fills + 10bp",True,10)):
    B=run(real,cost); print(f"\n{lab}")
    print(f"  {'setup':14s}{'n':>8s}{'win':>8s}{'exp (R)':>10s}{'t':>8s}{'max|R|':>9s}")
    for k in ("bounce","immediate","failure","no_breakout"):
        x=B[k]
        if len(x)<50: continue
        se=x.std()/np.sqrt(len(x))
        print(f"  {k:14s}{len(x):8,}{(x>0).mean():8.1%}{x.mean():+10.3f}{x.mean()/se:+8.2f}{np.abs(x).max():9.1f}")
    a_,b_=B["bounce"],B["no_breakout"]
    d=a_.mean()-b_.mean(); sed=np.sqrt(a_.var()/len(a_)+b_.var()/len(b_))
    print(f"  bounce - no_breakout = {d:+.3f}R  t = {d/sed:+.2f}")

print("\n\nR:R sweep on bounce, ATR stops, gap fills, 10bp")
print(f"{'R:R':>6s}{'breakeven':>11s}{'win':>8s}{'excess':>9s}{'exp(R)':>9s}{'exp/bar':>10s}{'t':>8s}")
for rr in (1,2,3,5,10):
    B=run(True,10,rr); x=B["bounce"]; be=1/(1+rr)
    se=x.std()/np.sqrt(len(x))
    print(f"{rr:6.1f}{be:11.1%}{(x>0).mean():8.1%}{(x>0).mean()-be:+9.1%}"
          f"{x.mean():+9.3f}{x.mean()/MAXBARS:+10.4f}{x.mean()/se:+8.2f}")
