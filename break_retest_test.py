"""Does break-and-retest actually work?  A direct test on real prices.

Probing a CNN measured the model's opinion of MY rendering of the pattern.
Three rounds went into whether my control points matched the textbook diagrams,
and the instrument (AUC 0.506) could not resolve the shapes anyway -- it gave
the same answer to a bullish setup and its exact vertical mirror.  So measure
the thing itself.

PRE-REGISTRATION -- fixed before looking at any result.

  Resistance at day t: the highest high over the prior L days, requiring at
  least MIN_TOUCH separate days whose high came within TOL of it.
  Breakout at b: first close above R*(1+BUF).
  Retest at r: first day within RWIN after b whose low returns to R*(1+TOL).
      bounce  -> close[r] still above R          (the strategy's entry)
      failure -> close[r] below R*(1-TOL)
  Control: a day where price touches R for the MIN_TOUCH+1'th time and does
      NOT break out -- same level, same approach, no breakout behind it.

  Statistic: mean MARKET-ADJUSTED forward FWD-day return from the entry close,
  where market-adjusted means minus that day's cross-sectional mean return
  across the panel.  Raw returns would just measure the 2010-2026 bull market.

  Primary comparison: bounce entries vs immediate-breakout entries.
  Reported with a t-stat clustered by calendar month, because overlapping
  windows and common market moves make naive iid standard errors far too small.

  Thresholds: an edge is claimed only if the difference is positive, |t| > 2
  after clustering, and survives the robustness grid at the end.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")

L, TOL, MIN_TOUCH, BUF, RWIN, FWD = 60, 0.01, 3, 0.005, 10, 5

df = pd.read_parquet("exploration/colab/colab_ohlcv.parquet")
df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
# market return per day = cross-sectional mean of next-FWD-day returns
piv = df.pivot_table(index="timestamp", columns="symbol", values="close")
fwd_all = piv.shift(-FWD)/piv - 1.0
mkt = fwd_all.mean(axis=1)

def scan(g, L=L, TOL=TOL, MIN_TOUCH=MIN_TOUCH, BUF=BUF, RWIN=RWIN):
    h,l,c = (g[k].values.astype(float) for k in ("high","low","close"))
    bad = g.bad_day.values; t = g.timestamp.values
    n = len(c); out = []
    if n < L+RWIN+FWD+2: return out
    for b in range(L, n-FWD-1):
        if bad[max(0,b-L):b+FWD+1].any(): continue
        R = h[b-L:b].max()
        if not np.isfinite(R) or R <= 0: continue
        touch = (h[b-L:b] >= R*(1-TOL)).sum()
        if touch < MIN_TOUCH: continue
        broke = c[b] > R*(1+BUF) and c[b-1] <= R*(1+BUF)
        if broke:
            out.append(("immediate", t[b], c[b+FWD]/c[b]-1.0))
            for r in range(b+1, min(b+1+RWIN, n-FWD)):
                if l[r] <= R*(1+TOL):                      # came back to the line
                    kind = "bounce" if c[r] > R else ("failure" if c[r] < R*(1-TOL) else None)
                    if kind: out.append((kind, t[r], c[r+FWD]/c[r]-1.0))
                    break
        else:
            # control: touches the level again without breaking out
            if h[b] >= R*(1-TOL) and c[b] <= R*(1+BUF) and h[b-1] < R*(1-TOL):
                out.append(("no_breakout", t[b], c[b+FWD]/c[b]-1.0))
    return out

rows = []
for j,(s,g) in enumerate(df.groupby("symbol", sort=False)):
    rows += scan(g)
    if j % 150 == 0: print(f"  {j} names, {len(rows):,} events", flush=True)
E = pd.DataFrame(rows, columns=["kind","date","fwd"])
E["date"] = pd.to_datetime(E.date)
E = E[np.isfinite(E.fwd) & (E.fwd.abs() < 1.0)]
E["adj"] = E.fwd - E.date.map(mkt).values
E["ym"] = E.date.dt.year*100 + E.date.dt.month

def clustered(x, by):
    """mean and t-stat with SEs clustered on calendar month"""
    m = x.mean()
    g = pd.DataFrame({"x":x,"g":by}).groupby("g").x.mean()
    se = g.std(ddof=1)/np.sqrt(len(g))
    return m, m/se if se > 0 else np.nan, len(x), len(g)

print(f"\n{len(E):,} events, {E.date.min().date()} .. {E.date.max().date()}\n")
print(f"{'setup':16s}{'n':>9s}{'mean adj':>11s}{'t (clust)':>11s}{'months':>8s}")
print("-"*56)
res = {}
for k in ("bounce","immediate","failure","no_breakout"):
    x = E[E.kind == k]
    if not len(x): continue
    m,t_,n_,ng = clustered(x.adj.values, x.ym.values)
    res[k] = (m,t_,n_)
    print(f"{k:16s}{n_:9,}{m:+11.4%}{t_:+11.2f}{ng:8d}")

if "bounce" in res and "immediate" in res:
    a = E[E.kind=="bounce"]; b = E[E.kind=="immediate"]
    ga = a.groupby("ym").adj.mean(); gb = b.groupby("ym").adj.mean()
    j = ga.index.intersection(gb.index); d = (ga[j]-gb[j])
    print(f"\nPRIMARY  bounce - immediate = {d.mean():+.4%}  "
          f"t = {d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):+.2f}  ({len(d)} months)")

# ---- is the 'failure' result driven by outliers, and does any of it survive? ----
print("\n" + "="*60)
print("distribution check -- a large mean on 1,702 events can be a few names")
print(f"{'setup':14s}{'mean':>9s}{'median':>9s}{'trim10%':>9s}{'%>0':>7s}{'max':>8s}")
for k in ("bounce","immediate","failure","no_breakout"):
    x = E[E.kind==k].adj.values
    lo,hi = np.percentile(x,[10,90]); tr = x[(x>=lo)&(x<=hi)].mean()
    print(f"{k:14s}{x.mean():+9.3%}{np.median(x):+9.3%}{tr:+9.3%}{(x>0).mean():7.1%}{x.max():+8.1%}")

print("\nbounce vs no_breakout (does the breakout matter at all?)")
ga = E[E.kind=="bounce"].groupby("ym").adj.mean(); gb = E[E.kind=="no_breakout"].groupby("ym").adj.mean()
j = ga.index.intersection(gb.index); d = ga[j]-gb[j]
print(f"  {d.mean():+.4%}  t = {d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):+.2f}")

print("\nfailure, excluding the most extreme 1% of events")
x = E[E.kind=="failure"]
cut = x.adj.abs().quantile(0.99); y = x[x.adj.abs() <= cut]
g = y.groupby("ym").adj.mean()
print(f"  n {len(y):,}  mean {y.adj.mean():+.3%}  "
      f"t = {g.mean()/(g.std(ddof=1)/np.sqrt(len(g))):+.2f}")
print("  by half-sample:")
for lab, sub in (("2010-2017", y[y.date < '2018-01-01']), ("2018-2026", y[y.date >= '2018-01-01'])):
    gg = sub.groupby("ym").adj.mean()
    print(f"    {lab}: n {len(sub):,}  mean {sub.adj.mean():+.3%}  "
          f"t = {gg.mean()/(gg.std(ddof=1)/np.sqrt(len(gg))):+.2f}")
