"""Render real intraday setups, so the detector can be checked by eye first.

Writes figures/intraday_setups.png
"""
import pandas as pd, numpy as np, glob, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, ".")
from intraday_levels import session_frames, find_setups, MIN_GAP, MIN_ADV, RWIN

NAMES = {"AAPL","MSFT","NVDA","AMD","TSLA","META","AMZN","SPY","QQQ","GOOGL","NFLX","JPM"}
files = sorted(glob.glob("cache/mp5min/*.parquet"))[-260:]        # most recent year

D = pd.read_parquet("cache/intraday_daily.parquet")
D = D[D.symbol.isin(NAMES)].sort_values(["symbol","date"])
prior = {(r.symbol, r.date): (r.pdh, r.pdl, r.pdc) for r in D.itertuples()}

EV = []
for s, dt, g in session_frames(files, NAMES):
    key = (s, dt)
    if key not in prior: continue
    pdh, pdl, pdc = prior[key]
    pre = g[g.h < 9.5]
    lv = {"PDH": pdh, "PDC": pdc,
          "ONH": pre.high.max() if len(pre) else None}
    for e in find_setups(g, lv):
        e.update(sym=s, date=dt, g=g)
        EV.append(e)
print(f"{len(EV)} setups found across {len(NAMES)} names, {len(files)} sessions")
if not EV: sys.exit("none found -- loosen the filters")

rng = np.random.default_rng(0)
bn = [e for e in EV if e["kind"]=="bounce"]; fl = [e for e in EV if e["kind"]=="failure"]
SEL = [bn[i] for i in rng.choice(len(bn), min(4,len(bn)), replace=False)] + \
      [fl[i] for i in rng.choice(len(fl), min(2,len(fl)), replace=False)]

fig, ax = plt.subplots(2, 3, figsize=(19, 9))
for a, e in zip(ax.ravel(), SEL):
    g = e["g"]; rth = g[(g.h>=9.5)&(g.h<16)].reset_index(drop=True)
    n = min(len(rth), e["entry"]+30)
    o,h,l,c = (rth[k].values[:n].astype(float) for k in ("open","high","low","close"))
    for i,(oo,hh,ll,cc) in enumerate(zip(o,h,l,c)):
        col = "#2ca02c" if cc>=oo else "#d62728"
        a.plot([i,i],[ll,hh], color=col, lw=.8)
        a.plot([i,i],[oo,cc], color=col, lw=3.0, solid_capstyle="butt")
    a.axhline(e["R"], color="#1f77b4", lw=1.8, label=f"{e['level']} {e['R']:.2f}")
    a.axvline(e["brk"],   color="#ff7f0e", lw=1.2, ls=":",  label="break")
    a.axvline(e["entry"], color="#111",    lw=1.6,          label="entry (retest)")
    adv = (h[e["brk"]+1:e["entry"]].max()-e["R"])/e["R"] if e["entry"]>e["brk"]+1 else 0
    a.set_title(f"{e['sym']}  {str(e['date'])[:10]}  {e['level']}-{e['kind']}   "
                f"{e['entry']-e['brk']} bars apart, advanced {adv:.2%}", fontsize=8)
    a.set_xlabel("5-min bars from 9:30", fontsize=7)
    a.tick_params(labelsize=7); a.legend(fontsize=6, loc="best")
fig.suptitle("Intraday prior-day-level breaks and retests.  "
             "Blue = level known before 9:30,  orange = break,  black = retest entry", fontsize=11)
plt.tight_layout()
import os; os.makedirs("figures", exist_ok=True)
plt.savefig("figures/intraday_setups.png", dpi=120, facecolor="white")
print("wrote figures/intraday_setups.png")
