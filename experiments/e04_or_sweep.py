"""E4: does the opening range get swept, then reverse?

Opening range = 9:30-10:00 high/low.  A "sweep" is price breaking the OR high
after 10:00 and then closing the session back inside.  The claim is that this
is a liquidity grab, so the break should fail more often than it holds.
"""
import pandas as pd, numpy as np
D = pd.read_parquet("cache/intraday_daily.parquet").dropna(subset=["hi_or","lo_or","hi_open","lo_open","c_rth"])
broke_h = D[D.hi_open > D.hi_or]          # took out the opening-range high after 10:00
broke_l = D[D.lo_open < D.lo_or]
print(f"{len(D):,} symbol-days\n")
print(f"broke the OR high after 10:00: {len(broke_h):,} ({len(broke_h)/len(D):.1%} of days)")
print(f"  ... closed back BELOW the OR high: {(broke_h.c_rth<broke_h.hi_or).mean():.1%}")
print(f"broke the OR low  after 10:00: {len(broke_l):,} ({len(broke_l)/len(D):.1%} of days)")
print(f"  ... closed back ABOVE the OR low : {(broke_l.c_rth>broke_l.lo_or).mean():.1%}")
print("\nIs fading the break profitable?  Move from the break level to the close:")
for lab,s,sign in (("faded OR-high break (short)",broke_h,-1),
                   ("faded OR-low  break (long)", broke_l,+1)):
    lvl = s.hi_or if sign<0 else s.lo_or
    x = sign*(s.c_rth/lvl - 1)
    t = x.mean()/(x.std()/np.sqrt(len(x)))
    print(f"  {lab:30s} n={len(s):7,}  mean {x.mean():+.4%}  t={t:+6.2f}  win {(x>0).mean():.1%}")
print("\nand holding the break instead (continuation):")
for lab,s,sign in (("held OR-high break (long)",broke_h,+1),
                   ("held OR-low  break (short)",broke_l,-1)):
    lvl = s.hi_or if sign>0 else s.lo_or
    x = sign*(s.c_rth/lvl - 1)
    t = x.mean()/(x.std()/np.sqrt(len(x)))
    print(f"  {lab:30s} n={len(s):7,}  mean {x.mean():+.4%}  t={t:+6.2f}  win {(x>0).mean():.1%}")
