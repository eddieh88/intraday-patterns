"""E6b: same setup, but the stop goes BELOW THE LEVEL.

Reported BY LEVEL, because prior-day close is touched far more often than the
prior day's extreme and would otherwise swamp the sample.

E6 put the stop below the ENTRY BAR's low, which came to 0.23% -- about one
5-minute bar's range, i.e. inside the noise.  74% of trades stopped and the
median outcome was -1.06R.

The stop for a break-and-retest belongs below THE LEVEL: the trade's premise is
that the level now holds as support, so the level breaking is what invalidates
it.  That is the red zone in every textbook diagram.  Here: level minus a
buffer of half a 5-minute ATR.
"""
import pandas as pd, numpy as np, glob, sys, time
sys.path.insert(0, ".")
from intraday_levels import session_frames, find_setups, MIN_GAP, MIN_ADV, RWIN

RR, COST_BP, ATR_N, ATR_MULT = 3.0, 2.0, 14, 0.5
files = sorted(glob.glob("cache/mp5min/*.parquet"))
D = pd.read_parquet("cache/intraday_daily.parquet")
dv = (D.c_rth*D.v_rth).groupby(D.symbol).sum()
NAMES = set(dv.nlargest(100).index)
D = D[D.symbol.isin(NAMES)]
prior = {(r.symbol, r.date): (r.pdh, r.pdl, r.pdc) for r in D.itertuples()}
print(f"{len(NAMES)} names, {len(files)} sessions", flush=True)

rows=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files, NAMES)):
    key=(s,dt)
    if key not in prior: continue
    pdh,pdl,pdc = prior[key]
    pre=g[g.h<9.5]
    lv={"PDH":pdh, "PDC":pdc, "ONH":(pre.high.max() if len(pre) else None)}
    ev=find_setups(g,lv)
    if not ev: continue
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
    pc=np.concatenate([[c[0]],c[:-1]])
    atr=pd.Series(np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))).rolling(ATR_N).mean().values
    for e in ev:
        r=e["entry"]; entry=c[r]
        a=atr[r] if np.isfinite(atr[r]) else (h[r]-l[r])
        stop=e["R"]-ATR_MULT*a               # below the LEVEL, not the entry bar
        risk=entry-stop
        if risk<=0 or risk/entry<0.0005: continue
        tgt=entry+RR*risk; cost=COST_BP*1e-4*entry
        out=None
        for j in range(r+1,len(c)):
            if l[j]<=stop: out=(min(stop,o[j])-entry-cost)/risk; break
            if h[j]>=tgt: out=(max(tgt,o[j])-entry-cost)/risk; break
        if out is None: out=(c[-1]-entry-cost)/risk
        rows.append(dict(sym=s,date=dt,level=e["level"],kind=e["kind"],
                         R=out, risk_pct=risk/entry))
    if i%20000==0 and i: print(f"  {i:,} sessions, {len(rows):,} trades, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows)
T.to_parquet("cache/e6b_trades.parquet", index=False)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")
print(f"{'level':8s}{'kind':10s}{'n':>8s}{'risk%':>8s}{'win':>8s}{'exp(R)':>9s}{'median':>9s}{'t':>8s}")
print("-"*70)
for (lv,k),g_ in T.groupby(["level","kind"]):
    if len(g_)<100: continue
    x=g_.R.values; se=x.std()/np.sqrt(len(x))
    print(f"{lv:8s}{k:10s}{len(x):8,}{g_.risk_pct.median():8.2%}{(x>0).mean():8.1%}"
          f"{x.mean():+9.3f}{np.median(x):+9.3f}{x.mean()/se:+8.2f}")
print("-"*70)
b=T[T.kind=="bounce"].R.values
print(f"{'ALL':8s}{'bounce':10s}{len(b):8,}{'':8s}{(b>0).mean():8.1%}"
      f"{b.mean():+9.3f}{np.median(b):+9.3f}{b.mean()/(b.std()/np.sqrt(len(b))):+8.2f}")
