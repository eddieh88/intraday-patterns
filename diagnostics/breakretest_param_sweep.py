"""Parameter sweep: does bounce-vs-no_breakout survive, or did I pick the numbers?

Six parameters were chosen to match the diagrams, not validated.  Sweep each
one around the pre-registered value, holding the others fixed, and report the
primary contrasts.  A result that appears only at the chosen setting was found
by searching, not measured.
"""
import numpy as np, pandas as pd, warnings, itertools, sys
warnings.filterwarnings("ignore")
BASE = dict(L=60, TOL=0.01, MIN_TOUCH=3, BUF=0.005, RWIN=10, FWD=5)

df = pd.read_parquet("exploration/colab/colab_ohlcv.parquet")
df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
piv = df.pivot_table(index="timestamp", columns="symbol", values="close")
GRP = list(df.groupby("symbol", sort=False))

def scan(g, L, TOL, MIN_TOUCH, BUF, RWIN, FWD):
    h,l,c = (g[k].values.astype(float) for k in ("high","low","close"))
    bad = g.bad_day.values; t = g.timestamp.values
    n = len(c); out = []
    if n < L+RWIN+FWD+2: return out
    for b in range(L, n-FWD-1):
        if bad[max(0,b-L):b+FWD+1].any(): continue
        R = h[b-L:b].max()
        if not np.isfinite(R) or R <= 0: continue
        if (h[b-L:b] >= R*(1-TOL)).sum() < MIN_TOUCH: continue
        if c[b] > R*(1+BUF) and c[b-1] <= R*(1+BUF):
            out.append(("immediate", t[b], c[b+FWD]/c[b]-1.0))
            for r in range(b+1, min(b+1+RWIN, n-FWD)):
                if l[r] <= R*(1+TOL):
                    k = "bounce" if c[r] > R else ("failure" if c[r] < R*(1-TOL) else None)
                    if k: out.append((k, t[r], c[r+FWD]/c[r]-1.0))
                    break
        elif h[b] >= R*(1-TOL) and c[b] <= R*(1+BUF) and h[b-1] < R*(1-TOL):
            out.append(("no_breakout", t[b], c[b+FWD]/c[b]-1.0))
    return out

def run(**kw):
    p = {**BASE, **kw}
    mkt = (piv.shift(-p["FWD"])/piv - 1.0).mean(axis=1)
    rows = []
    for s,g in GRP: rows += scan(g, **p)
    E = pd.DataFrame(rows, columns=["kind","date","fwd"])
    E["date"] = pd.to_datetime(E.date)
    E = E[np.isfinite(E.fwd) & (E.fwd.abs() < 1.0)]
    E["adj"] = E.fwd - E.date.map(mkt).values
    E["ym"] = E.date.dt.year*100 + E.date.dt.month
    def diff(a,b):
        ga = E[E.kind==a].groupby("ym").adj.mean(); gb = E[E.kind==b].groupby("ym").adj.mean()
        j = ga.index.intersection(gb.index)
        if len(j) < 24: return np.nan, np.nan
        d = ga[j]-gb[j]
        return d.mean(), d.mean()/(d.std(ddof=1)/np.sqrt(len(d)))
    nb = len(E[E.kind=="bounce"])
    return diff("bounce","no_breakout"), diff("bounce","immediate"), nb

print(f"{'variant':22s}{'bounce - no_breakout':>26s}{'bounce - immediate':>24s}{'n':>9s}")
print(f"{'':22s}{'mean':>13s}{'t':>13s}{'mean':>13s}{'t':>11s}")
print("-"*82)
GRID = [("BASE (pre-registered)", {})]
for v in (30,90,120):      GRID.append((f"L = {v}",         dict(L=v)))
for v in (0.005,0.02):     GRID.append((f"TOL = {v}",       dict(TOL=v)))
for v in (2,4,5):          GRID.append((f"MIN_TOUCH = {v}", dict(MIN_TOUCH=v)))
for v in (0.0,0.01,0.02):  GRID.append((f"BUF = {v}",       dict(BUF=v)))
for v in (5,15,20):        GRID.append((f"RWIN = {v}",      dict(RWIN=v)))
for v in (1,10,21):        GRID.append((f"FWD = {v}",       dict(FWD=v)))
out=[]
for lab,kw in GRID:
    (m1,t1),(m2,t2),n = run(**kw); out.append((lab,m1,t1,m2,t2,n))
    print(f"{lab:22s}{m1:+13.4%}{t1:+13.2f}{m2:+13.4%}{t2:+11.2f}{n:9,}", flush=True)
a=np.array([o[2] for o in out]); b=np.array([o[4] for o in out])
print("-"*82)
print(f"bounce - no_breakout : {(a>2).sum()}/{len(a)} variants with t>2, median t {np.nanmedian(a):+.2f}")
print(f"bounce - immediate   : {(b>2).sum()}/{len(b)} variants with t>2, median t {np.nanmedian(b):+.2f}")
