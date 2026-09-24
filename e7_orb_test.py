"""E7 pass 2: simulate the ORB on Stocks in Play.  Rules fixed in PREREG_orb.md.

Entry  : first 5-min close beyond the 09:30-09:35 range, in the direction that
         bar closed.
Stop   : A = opposite side of the opening range;  B = 1.5 x ATR(14) from entry.
Exit   : market close.  No profit target.
Costs  : 2bp round trip; stops fill at min/max(stop, next open) so gaps count.
"""
import pandas as pd, numpy as np, glob, time, sys

COST_BP, ATR_MULT, TOPN = 2.0, 1.5, 20
D = pd.read_parquet("cache/orb_daily.parquet").dropna(subset=["dv20","orv14","atr14","relvol"])
F = D[(D.o_rth > 5) & (D.atr14 > 0.5)].copy()
F = F[F.groupby("date").dv20.rank(ascending=False, method="first") <= 1000]
F["rk"] = F.groupby("date").relvol.rank(ascending=False, method="first")
sel = {}                       # date -> {symbol: (or_h, or_l, or_dir, atr, rank)}
for r in F[F.rk <= 200].itertuples():      # keep 200 so top-20 vs rest can be compared
    sel.setdefault(r.date, {})[r.symbol] = (r.or_h, r.or_l,
                                            1 if r.or_c >= r.or_o else -1, r.atr14, r.rk)
print(f"{len(sel):,} sessions with selections", flush=True)

def simulate(o,h,l,c,orh,orl,d,atr):
    """-> (R_stopA, R_stopB) or None.  Bars are 5-min RTH from 09:35 onward."""
    for i in range(len(c)):
        if d>0 and c[i]>orh: e=i; entry=c[i]; break
        if d<0 and c[i]<orl: e=i; entry=c[i]; break
    else: return None
    out=[]
    for stop in (orl if d>0 else orh, entry-d*ATR_MULT*atr):
        risk=abs(entry-stop)
        if risk<=0 or risk/entry<0.0005: out.append(np.nan); continue
        cost=COST_BP*1e-4*entry; res=None
        for j in range(e+1,len(c)):
            if d>0 and l[j]<=stop: res=(min(stop,o[j])-entry-cost)/risk; break
            if d<0 and h[j]>=stop: res=(entry-max(stop,o[j])-cost)/risk; break
        if res is None: res=(d*(c[-1]-entry)-cost)/risk
        out.append(res)
    return out

files=sorted(glob.glob("cache/mp5min/*.parquet"))
rows=[]; t0=time.time()
for k,f in enumerate(files):
    d0=pd.read_parquet(f, columns=["timestamp","symbol","open","high","low","close"])
    d0["symbol"]=d0.symbol.str.replace("-DELISTED","",regex=False)
    t=pd.to_datetime(d0.timestamp); dt=t.iloc[0].normalize()
    if dt not in sel: continue
    S=sel[dt]
    d0=d0.assign(hh=t.dt.hour+t.dt.minute/60)     # attach BEFORE filtering, so the
    d0=d0[d0.symbol.isin(S)]                       # mask cannot be misaligned later
    d0=d0[(d0.hh>=9.5+5/60)&(d0.hh<16)].sort_values("timestamp")   # from 09:35
    for s,g in d0.groupby("symbol"):
        orh,orl,dirn,atr,rk=S[s]
        if not np.isfinite([orh,orl,atr]).all(): continue
        o,h_,l_,c_=(g[x].values.astype(float) for x in ("open","high","low","close"))
        if len(c_)<10: continue
        r=simulate(o,h_,l_,c_,orh,orl,dirn,atr)
        if r is None: continue
        rows.append(dict(date=dt,sym=s,rk=rk,dir=dirn,A=r[0],B=r[1]))
    if k%200==0 and k: print(f"  {k}/{len(files)}  {len(rows):,} trades  {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e7_trades.parquet",index=False)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")
def rep(lab,x):
    x=x[np.isfinite(x)]
    if len(x)<100: return
    se=x.std()/np.sqrt(len(x))
    print(f"{lab:28s}{len(x):9,}{(x>0).mean():8.1%}{x.mean():+10.3f}{np.median(x):+9.3f}{x.mean()/se:+8.2f}")
print(f"{'group':28s}{'n':>9s}{'win':>8s}{'mean R':>10s}{'median':>9s}{'t':>8s}")
print("-"*72)
for lab,sub in (("top 20 relvol",T[T.rk<=20]),("rank 21-50",T[(T.rk>20)&(T.rk<=50)]),
                ("rank 51-200",T[T.rk>50])):
    rep(f"  {lab}  stop=OR",  sub.A.values)
    rep(f"  {lab}  stop=1.5ATR", sub.B.values)
