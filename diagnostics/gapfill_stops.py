"""Realistic fills: stops gap through, and costs are not zero.

The bracket test assumed a stop fills at exactly -1R.  Real stops fill at the
OPEN when a bar gaps past them, which is worse and asymmetric.  Targets gap in
your favour too, but the two do not cancel: downside gaps in equities are
larger and more frequent than upside gaps of the same size.

Adds, on top of the idealised version:
  * stop fills at min(stop, open[i]) -- gap through
  * target fills at max(target, open[i]) -- gap in favour
  * COST charged on entry and exit as a fraction of the entry price
"""
import numpy as np, pandas as pd, warnings, sys
warnings.filterwarnings("ignore")
sys.path.insert(0, "lib")
from swing_levels import scan_trades

RR, MAXBARS, PAD = 3.0, 20, 0.002

def bracket(o,h,l,c,e, realistic, cost_bp):
    entry=c[e]; stop=l[e]*(1-PAD); risk=entry-stop
    if not np.isfinite(risk) or risk<=0: return None
    target=entry+RR*risk
    cost=(cost_bp*1e-4)*entry*2            # round trip, as a price amount
    for i in range(e+1, min(e+1+MAXBARS, len(c))):
        hit_s = l[i]<=stop; hit_t = h[i]>=target
        if hit_s:
            fill = min(stop, o[i]) if realistic else stop
            return (fill-entry-cost)/risk
        if hit_t:
            fill = max(target, o[i]) if realistic else target
            return (fill-entry-cost)/risk
    j=min(e+MAXBARS, len(c)-1)
    return (c[j]-entry-cost)/risk

df = pd.read_parquet("colab/colab_ohlcv.parquet")
df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
GR = list(df.groupby("symbol", sort=False))

def run(realistic, cost_bp):
    B={k:[] for k in ("bounce","immediate","failure","no_breakout")}
    for s,g in GR:
        o,h,l,c = (g[k].values.astype(float) for k in ("open","high","low","close"))
        for kind,e in scan_trades(g):
            r=bracket(o,h,l,c,e,realistic,cost_bp)
            if r is not None: B[kind].append(r)
    return {k:np.array(v) for k,v in B.items()}

for lab, realistic, cost in (("idealised, 0 cost", False, 0),
                             ("gap fills, 0 cost", True, 0),
                             ("gap fills + 5bp",   True, 5),
                             ("gap fills + 10bp",  True, 10)):
    B=run(realistic, cost)
    print(f"\n{lab}")
    print(f"  {'setup':14s}{'n':>8s}{'win':>8s}{'exp (R)':>10s}{'t':>8s}")
    for k in ("bounce","immediate","failure","no_breakout"):
        x=B[k]
        if len(x)<50: continue
        se=x.std()/np.sqrt(len(x))
        print(f"  {k:14s}{len(x):8,}{(x>0).mean():8.1%}{x.mean():+10.3f}{x.mean()/se:+8.2f}")
    a,b=B["bounce"],B["no_breakout"]
    d=a.mean()-b.mean(); sed=np.sqrt(a.var()/len(a)+b.var()/len(b))
    print(f"  bounce - no_breakout = {d:+.3f}R  t = {d/sed:+.2f}")
