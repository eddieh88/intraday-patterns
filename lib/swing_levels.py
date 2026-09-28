"""Support/resistance from SWING POINTS, the way levels are actually drawn.

The first version used a rolling max and counted days within 1% of it.  Two
problems.  A rolling max is the single highest print, not a level price
respected repeatedly.  And counting DAYS conflates one three-day push with
three separate visits -- the thing that makes a level real.

Here a swing high is a local pivot: a bar whose high exceeds the K bars on
either side.  Swing highs are then clustered by price, and a level is a cluster
containing at least MIN_SWINGS distinct pivots.  Everything is measured in BARS,
not days, so the same code applies to a 5-minute chart given 5-minute data --
only K and LOOKBACK change meaning.

LOOK-AHEAD: a pivot at bar i is only confirmed at bar i+K, because it needs the
K bars after it.  At decision bar b only pivots with i <= b-K-1 may be used.
Using unconfirmed pivots would leak the future, which is the bug that cost this
project a 19%/yr artifact earlier today.
"""
import numpy as np, pandas as pd

K, LOOKBACK, CLUST, MIN_SWINGS, BUF, RWIN, FWD = 3, 60, 0.015, 3, 0.005, 10, 5

def swing_highs(h, K):
    """bar i is a pivot high if its high is the max of the 2K+1 window centred on it"""
    n = len(h); out = np.zeros(n, bool)
    for i in range(K, n-K):
        w = h[i-K:i+K+1]
        if np.isfinite(w).all() and h[i] == w.max() and (w[:K] < h[i]).all():
            out[i] = True
    return out

def levels_at(b, piv_idx, h, CLUST, MIN_SWINGS, K):
    """cluster CONFIRMED pivot highs into price levels; return the best one below price"""
    usable = piv_idx[(piv_idx <= b-K-1) & (piv_idx >= b-LOOKBACK)]
    if len(usable) < MIN_SWINGS: return None
    p = np.sort(h[usable])
    best = None
    for i in range(len(p)):
        grp = p[(p >= p[i]) & (p <= p[i]*(1+CLUST))]     # cluster within CLUST
        if len(grp) >= MIN_SWINGS:
            lvl = grp.mean()
            if best is None or len(grp) > best[1]: best = (lvl, len(grp))
    return None if best is None else best[0]

def scan(g):
    h,l,c = (g[k].values.astype(float) for k in ("high","low","close"))
    bad = g.bad_day.values; t = g.timestamp.values; n = len(c)
    if n < LOOKBACK+RWIN+FWD+2*K+2: return []
    piv = np.flatnonzero(swing_highs(h, K))
    out = []
    for b in range(LOOKBACK, n-FWD-1):
        if bad[max(0,b-LOOKBACK):b+FWD+1].any(): continue
        R = levels_at(b, piv, h, CLUST, MIN_SWINGS, K)
        if R is None or not np.isfinite(R) or R <= 0: continue
        if c[b-1] <= R*(1+BUF) < c[b]:                       # first close above the level
            out.append(("immediate", t[b], c[b+FWD]/c[b]-1.0))
            for r in range(b+1, min(b+1+RWIN, n-FWD)):
                if l[r] <= R*(1+CLUST/2):                    # low returns to the level
                    k = "bounce" if c[r] > R else ("failure" if c[r] < R*(1-CLUST/2) else None)
                    if k: out.append((k, t[r], c[r+FWD]/c[r]-1.0))
                    break
        elif h[b] >= R*(1-CLUST/2) and c[b] <= R*(1+BUF) and h[b-1] < R*(1-CLUST/2):
            out.append(("no_breakout", t[b], c[b+FWD]/c[b]-1.0))
    return out

def scan_trades(g):
    """same detection, but returns (kind, entry_bar_index) so a bracket can be simulated"""
    h,l,c = (g[k].values.astype(float) for k in ("high","low","close"))
    bad = g.bad_day.values; n = len(c)
    if n < LOOKBACK+RWIN+FWD+2*K+2: return []
    piv = np.flatnonzero(swing_highs(h, K)); out = []
    for b in range(LOOKBACK, n-FWD-1):
        if bad[max(0,b-LOOKBACK):b+FWD+1].any(): continue
        R = levels_at(b, piv, h, CLUST, MIN_SWINGS, K)
        if R is None or not np.isfinite(R) or R <= 0: continue
        if c[b-1] <= R*(1+BUF) < c[b]:
            out.append(("immediate", b))
            for r in range(b+1, min(b+1+RWIN, n-FWD)):
                if l[r] <= R*(1+CLUST/2):
                    k = "bounce" if c[r] > R else ("failure" if c[r] < R*(1-CLUST/2) else None)
                    if k: out.append((k, r))
                    break
        elif h[b] >= R*(1-CLUST/2) and c[b] <= R*(1+BUF) and h[b-1] < R*(1-CLUST/2):
            out.append(("no_breakout", b))
    return out

if __name__ == "__main__":
    df = pd.read_parquet("colab/colab_ohlcv.parquet")
    df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
    piv = df.pivot_table(index="timestamp", columns="symbol", values="close")
    mkt = (piv.shift(-FWD)/piv - 1.0).mean(axis=1)
    rows = []
    for j,(s,g) in enumerate(df.groupby("symbol", sort=False)):
        rows += scan(g)
        if j % 150 == 0: print(f"  {j} names, {len(rows):,} events", flush=True)
    E = pd.DataFrame(rows, columns=["kind","date","fwd"])
    E["date"] = pd.to_datetime(E.date)
    E = E[np.isfinite(E.fwd) & (E.fwd.abs() < 1.0)]
    E["adj"] = E.fwd - E.date.map(mkt).values
    E["ym"] = E.date.dt.year*100 + E.date.dt.month
    print(f"\nSWING-BASED LEVELS: K={K} bars, >={MIN_SWINGS} pivots clustered within {CLUST:.1%}")
    print(f"{len(E):,} events\n")
    print(f"{'setup':14s}{'n':>9s}{'mean adj':>11s}{'median':>10s}{'t (clust)':>11s}")
    print("-"*55)
    for k in ("bounce","immediate","failure","no_breakout"):
        x = E[E.kind==k]
        if not len(x): continue
        gm = x.groupby("ym").adj.mean()
        t_ = gm.mean()/(gm.std(ddof=1)/np.sqrt(len(gm)))
        print(f"{k:14s}{len(x):9,}{x.adj.mean():+11.4%}{x.adj.median():+10.4%}{t_:+11.2f}")
    for a,b_ in (("bounce","immediate"),("bounce","no_breakout")):
        ga=E[E.kind==a].groupby("ym").adj.mean(); gb=E[E.kind==b_].groupby("ym").adj.mean()
        j=ga.index.intersection(gb.index); d=ga[j]-gb[j]
        print(f"\n{a} - {b_}: {d.mean():+.4%}  t = {d.mean()/(d.std(ddof=1)/np.sqrt(len(d))):+.2f}")
