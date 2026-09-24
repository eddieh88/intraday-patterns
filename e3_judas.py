"""E3: is the opening move a false move that reverses? (PO3 / 'judas swing')

Claim: the 9:30-10:00 move is manipulation, and the real move goes the other
way.  Testable: does the sign of the opening-range move predict the sign of
the 10:00-11:00 move?  50% reversal = no information.
"""
import pandas as pd, numpy as np
from scipy import stats
D = pd.read_parquet("cache/intraday_daily.parquet").dropna(subset=["o_or","c_or","o_open","c_open","pdc"])
D["or_move"]   = D.c_or/D.o_or - 1          # 9:30 -> 10:00
D["next_move"] = D.c_open/D.o_open - 1      # 10:00 -> 11:00
D["gap"]       = D.o_or/D.pdc - 1
s = D[D.or_move != 0]
rev  = (np.sign(s.next_move) != np.sign(s.or_move)).mean()
r,p  = stats.pearsonr(s.or_move, s.next_move)
print(f"{len(s):,} symbol-days\n")
print(f"reversal rate                 {rev:.1%}    (50.0% = no information)")
print(f"corr(9:30-10:00, 10:00-11:00) {r:+.4f}   p={p:.2e}")
print(f"\nby size of the opening move:")
print(f"{'opening move':18s}{'n':>9s}{'reversal':>11s}{'next-move mean':>17s}")
for lo,hi,lab in ((0,.003,"<0.3%"),(.003,.007,"0.3-0.7%"),(.007,.015,"0.7-1.5%"),(.015,9,">1.5%")):
    x=s[(s.or_move.abs()>=lo)&(s.or_move.abs()<hi)]
    if len(x)<500: continue
    rv=(np.sign(x.next_move)!=np.sign(x.or_move)).mean()
    cont=(x.next_move*np.sign(x.or_move)).mean()
    print(f"{lab:18s}{len(x):9,}{rv:11.1%}{cont:+17.4%}")
print("\n  'next-move mean' is signed to the opening direction:")
print("  positive = CONTINUATION, negative = REVERSAL")
