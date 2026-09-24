"""E5: does the pre-market session predict the 9:30-11:00 move?

The falsifiable core of "the market tells you the day's direction before 9:30".
Our data starts at 04:00 ET, covering the London session.
"""
import pandas as pd, numpy as np
from scipy import stats
D = pd.read_parquet("cache/intraday_daily.parquet").dropna(subset=["c_pre","pdc","o_or","c_open","pdh","pdl","hi_pre","lo_pre"])
D["pre_ret"]  = D.c_pre/D.pdc - 1          # overnight move
D["open_ret"] = D.c_open/D.o_or - 1        # 9:30 -> 11:00
print(f"{len(D):,} symbol-days\n")
r,p = stats.pearsonr(D.pre_ret, D.open_ret)
same = (np.sign(D.pre_ret)==np.sign(D.open_ret)).mean()
print(f"1. DIRECTION")
print(f"   corr(pre-market, 9:30-11:00) = {r:+.4f}  p={p:.1e}")
print(f"   same-direction rate {same:.1%}   (50% = no information)")
for lo,hi,lab in ((0,.005,"<0.5%"),(.005,.015,"0.5-1.5%"),(.015,9,">1.5%")):
    s=D[(D.pre_ret.abs()>=lo)&(D.pre_ret.abs()<hi)]
    if len(s)<500: continue
    print(f"     pre-market move {lab:9s} n={len(s):6,}  same-direction "
          f"{(np.sign(s.pre_ret)==np.sign(s.open_ret)).mean():.1%}")
print(f"\n2. SWEEP AND REVERSE ('the 6 AM candle confirms it')")
sh = D[(D.hi_pre>D.pdh)&(D.c_pre<D.pdh)]   # swept prior high, closed back below -> bearish
sl = D[(D.lo_pre<D.pdl)&(D.c_pre>D.pdl)]   # swept prior low, closed back above  -> bullish
base = (D.open_ret>0).mean()
print(f"   unconditional: 9:30-11:00 up {base:.1%}  <- benchmark")
for lab,s,want in (("swept prior HIGH -> short",sh,-1),("swept prior LOW -> long",sl,+1)):
    if len(s)<200: continue
    x = want*s.open_ret
    t = x.mean()/(x.std()/np.sqrt(len(x)))
    print(f"   {lab:26s} n={len(s):6,}  mean {x.mean():+.4%}  t={t:+6.2f}  win {(x>0).mean():.1%}")
