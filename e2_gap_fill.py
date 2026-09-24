"""E2: do opening gaps fill in the same session?

Gap = prior RTH close -> today's 9:30 open.  "Filled" = price trades back
through the prior close at some point during RTH.
"""
import pandas as pd, numpy as np
D = pd.read_parquet("cache/intraday_daily.parquet").dropna(subset=["pdc","o_or"])
D["gap"] = D.o_or/D.pdc - 1
D["filled"] = np.where(D.gap>0, D.lo_rth<=D.pdc, D.hi_rth>=D.pdc)
up, dn = D[D.gap>0], D[D.gap<0]
print(f"{len(D):,} symbol-days, {D.date.nunique()} sessions\n")
print(f"{'gap size':18s}{'n':>9s}{'gap up fills':>14s}{'gap down fills':>16s}")
print("-"*58)
for lo,hi,lab in ((0,.002,"<0.2%"),(.002,.005,"0.2-0.5%"),(.005,.01,"0.5-1%"),
                  (.01,.02,"1-2%"),(.02,9,">2%")):
    s=D[(D.gap.abs()>=lo)&(D.gap.abs()<hi)]
    if len(s)<200: continue
    u=s[s.gap>0]; d_=s[s.gap<0]
    print(f"{lab:18s}{len(s):9,}{u.filled.mean():14.1%}{d_.filled.mean():16.1%}")
print("-"*58)
print(f"{'ALL':18s}{len(D):9,}{up.filled.mean():14.1%}{dn.filled.mean():16.1%}")
print(f"\nA gap that fills is not automatically tradeable: the question is whether")
print(f"fading it pays after the adverse excursion first.  Mean move from the")
print(f"9:30 open to the 11:00 close, by gap direction:")
D["open_move"]=D.c_open/D.o_or-1
for lab,s in (("gap up  >0.5%",D[D.gap>.005]),("gap down >0.5%",D[D.gap<-.005])):
    print(f"  {lab:16s} n={len(s):6,}  mean {s.open_move.mean():+.4%}  "
          f"median {s.open_move.median():+.4%}  up {(s.open_move>0).mean():.1%}")
