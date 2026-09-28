"""E9: what does the trade DO after entry?

Mean R hides the path.  A -0.073R average could be trades that die instantly,
or trades that run to +2.9R and give it all back.  Those need opposite fixes.

Per trade, measured bar by bar from entry to the 16:00 close:
  MFE   max favourable excursion, in R
  MAE   max adverse excursion, in R
  t_MFE bars until the best point
  t_MAE bars until the worst point
and the average R path, separately for eventual winners and losers.
"""
import pandas as pd, numpy as np, glob, sys, time
from intraday_levels import session_frames, find_setups
MAXB=60

files=sorted(glob.glob("cache/mp5min/*.parquet"))
D=pd.read_parquet("cache/intraday_daily.parquet")
dv=(D.c_rth*D.v_rth).groupby(D.symbol).sum(); NAMES=set(dv.nlargest(100).index)
D=D[D.symbol.isin(NAMES)]
prior={(r.symbol,r.date):(r.pdh,r.pdl,r.pdc) for r in D.itertuples()}
rows=[]; paths=[]; t0=time.time()
for i,(s,dt,g) in enumerate(session_frames(files,NAMES)):
    if (s,dt) not in prior: continue
    pdh,pdl,pdc=prior[(s,dt)]; pre=g[g.h<9.5]
    ev=find_setups(g,{"PDH":pdh,"PDC":pdc,"ONH":pre.high.max() if len(pre) else None})
    if not ev: continue
    rth=g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    o,h,l,c=(rth[k].values.astype(float) for k in ("open","high","low","close"))
    for e in ev:
        if e["kind"]!="bounce": continue
        r=e["entry"]; entry=c[r]; stop=e["R"]-0.5*(h[r]-l[r]); risk=entry-stop
        if risk<=0 or risk/entry<0.0005: continue
        n=min(len(c)-r-1,MAXB)
        if n<6: continue
        up=(h[r+1:r+1+n]-entry)/risk          # favourable path
        dn=(l[r+1:r+1+n]-entry)/risk          # adverse path
        cl=(c[r+1:r+1+n]-entry)/risk
        # the trade as actually exited: stop at -1R else close
        stopped=np.flatnonzero(dn<=-1.0)
        final=-1.0 if len(stopped) else cl[-1]
        tstop=int(stopped[0])+1 if len(stopped) else np.nan
        # MFE before the stop fires
        cut=int(stopped[0]) if len(stopped) else n
        mfe=up[:cut+1].max() if cut>=0 else up[0]
        rows.append(dict(mfe=float(mfe), mae=float(dn.min()), final=float(final),
                         t_mfe=int(np.argmax(up[:cut+1]))+1 if cut>=0 else 1,
                         t_stop=tstop, n=n))
        p=np.full(MAXB,np.nan); p[:n]=cl; paths.append((final>0,p))
    if i%25000==0 and i: print(f"  {i:,} sessions, {len(rows):,} trades, {time.time()-t0:.0f}s",flush=True)

T=pd.DataFrame(rows); T.to_parquet("cache/e9_path.parquet",index=False)
P=np.array([p for _,p in paths]); W=np.array([w for w,_ in paths])
np.save("cache/e9_paths.npy",P); np.save("cache/e9_win.npy",W)
print(f"\n{len(T):,} trades  ({time.time()-t0:.0f}s)\n")
win=T.final>0
print(f"{'':22s}{'ALL':>12s}{'winners':>12s}{'losers':>12s}")
print("-"*58)
for lab,col in (("MFE (best point, R)","mfe"),("MAE (worst point, R)","mae"),
                ("bars to MFE","t_mfe")):
    print(f"{lab:22s}{T[col].median():12.2f}{T[col][win].median():12.2f}{T[col][~win].median():12.2f}")
print(f"{'n':22s}{len(T):12,}{win.sum():12,}{(~win).sum():12,}")
print(f"\nLOSERS -- did they go green first?")
lz=T[~win]
for lo,hi,lab in ((0,.25,"never above +0.25R"),(.25,.5,"+0.25 to +0.5R"),(.5,1,"+0.5 to +1R"),
                  (1,2,"+1 to +2R"),(2,99,"above +2R")):
    m=(lz.mfe>=lo)&(lz.mfe<hi)
    print(f"  reached {lab:20s} {m.mean():6.1%}   median bars to that peak: {lz.t_mfe[m].median():.0f}")
print(f"\n  median bars from entry to the stop firing: {T.t_stop.median():.0f}  "
      f"({T.t_stop.median()*5:.0f} minutes)")
print(f"\nWINNERS -- how far against them first?")
wz=T[win]
for lo,hi,lab in ((-99,-.75,"worse than -0.75R"),(-.75,-.5,"-0.75 to -0.5R"),
                  (-.5,-.25,"-0.5 to -0.25R"),(-.25,0,"-0.25 to 0")):
    m=(wz.mae>=lo)&(wz.mae<hi)
    print(f"  dipped to {lab:20s} {m.mean():6.1%}")
