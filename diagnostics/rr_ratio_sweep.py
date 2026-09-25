"""Is 1:3 optimal, or just convention?

For a driftless random walk the probability of reaching +RR*R before -1R is
exactly 1/(1+RR), so EVERY ratio has zero expectancy and the choice is
arbitrary.  Real prices differ: upward drift, a finite time limit, volatility
clustering and gaps all break the martingale.  So sweep it.
"""
import numpy as np, pandas as pd, warnings, sys
warnings.filterwarnings("ignore")
sys.path.insert(0, "lib")
from swing_levels import scan_trades
MAXBARS, PAD = 20, 0.002

def bracket(o,h,l,c,e,rr):
    entry=c[e]; stop=l[e]*(1-PAD); risk=entry-stop
    if not np.isfinite(risk) or risk<=0: return None
    target=entry+rr*risk
    for i in range(e+1, min(e+1+MAXBARS,len(c))):
        if l[i]<=stop:  return (min(stop,o[i])-entry)/risk
        if h[i]>=target: return (max(target,o[i])-entry)/risk
    j=min(e+MAXBARS,len(c)-1)
    return (c[j]-entry)/risk

df=pd.read_parquet("colab/colab_ohlcv.parquet").sort_values(["symbol","timestamp"])
GR=list(df.groupby("symbol",sort=False))
TR=[]
for s,g in GR:
    o,h,l,c=(g[k].values.astype(float) for k in ("open","high","low","close"))
    for kind,e in scan_trades(g):
        if kind=="bounce": TR.append((o,h,l,c,e))
print(f"{len(TR):,} bounce setups\n")
print(f"{'R:R':>6s}{'breakeven':>11s}{'win rate':>10s}{'excess':>9s}{'exp (R)':>10s}{'t':>8s}{'%timeout':>10s}")
print("-"*64)
best=None
for rr in (0.5,1,1.5,2,2.5,3,4,5,7,10):
    xs=[]; to=0
    for o,h,l,c,e in TR:
        r=bracket(o,h,l,c,e,rr)
        if r is None: continue
        xs.append(r)
        if abs(r-rr)>1e-9 and abs(r+1)>1e-9: to+=1
    x=np.array(xs); be=1/(1+rr); win=(x>0).mean()
    se=x.std()/np.sqrt(len(x))
    print(f"{rr:6.1f}{be:11.1%}{win:10.1%}{win-be:+9.1%}{x.mean():+10.3f}{x.mean()/se:+8.2f}{to/len(x):10.1%}")
    if best is None or x.mean()>best[1]: best=(rr,x.mean())
print("-"*64)
print(f"best expectancy at R:R = {best[0]:.1f}  ({best[1]:+.3f}R)")
print("\nnote: expectancy in R units is not the same as dollars per unit time --")
print("higher ratios take longer to resolve, so compare exp(R) per bar too.")
