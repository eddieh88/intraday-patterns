"""Two-day view: where the level comes from, and how it is acted on.

Left half of each panel is the PRIOR session (which defines PDH/PDC/PDL and the
overnight range).  Right half is the trade day.  The level is drawn across both
so its origin is visible rather than asserted.
"""
import pandas as pd, numpy as np, glob, sys, os, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, "lib")
from intraday_levels import find_setups, MIN_GAP, MIN_ADV, RWIN

NAMES={"AAPL","MSFT","NVDA","AMD","TSLA","META","AMZN","GOOGL","NFLX","JPM","COST","AVGO"}
files=sorted(glob.glob("cache/mp5min/*.parquet"))[-200:]
D=pd.read_parquet("cache/intraday_daily.parquet")
D=D[D.symbol.isin(NAMES)].sort_values(["symbol","date"])
prior={(r.symbol,r.date):(r.pdh,r.pdl,r.pdc) for r in D.itertuples()}

# keep each session's bars so the prior day can be redrawn
cache={}
EV=[]
for f in files:
    d=pd.read_parquet(f,columns=["timestamp","symbol","open","high","low","close"])
    d["symbol"]=d.symbol.str.replace("-DELISTED","",regex=False)
    d=d[d.symbol.isin(NAMES)]
    if not len(d): continue
    t=pd.to_datetime(d.timestamp); dt=t.iloc[0].normalize()
    d=d.assign(ts=t,h=t.dt.hour+t.dt.minute/60).sort_values("ts")
    for s,g in d.groupby("symbol"):
        cache[(s,dt)]=g.reset_index(drop=True)
        if (s,dt) not in prior: continue
        pdh,pdl,pdc=prior[(s,dt)]
        pre=g[g.h<9.5]
        lv={"PDH":pdh,"PDC":pdc,"ONH":pre.high.max() if len(pre) else None}
        for e in find_setups(g,lv):
            e.update(sym=s,date=dt); EV.append(e)
print(f"{len(EV)} setups")

dates=sorted({d for _,d in cache})
prev_of={d:dates[i-1] for i,d in enumerate(dates) if i}
usable=[e for e in EV if (e["sym"],prev_of.get(e["date"])) in cache]
rng=np.random.default_rng(1)
SEL=[usable[i] for i in rng.choice(len(usable),min(4,len(usable)),replace=False)]

fig,ax=plt.subplots(2,2,figsize=(17,9))
for a,e in zip(ax.ravel(),SEL):
    pdate=prev_of[e["date"]]
    pg=cache[(e["sym"],pdate)]; tg=cache[(e["sym"],e["date"])]
    prth=pg[(pg.h>=9.5)&(pg.h<16)].reset_index(drop=True)
    tall=tg[tg.h>=4].reset_index(drop=True)                 # incl. pre-market
    trth_start=int((tall.h>=9.5).values.argmax())
    seq=pd.concat([prth,tall],ignore_index=True)
    off=len(prth)
    for i,r in seq.iterrows():
        col="#2ca02c" if r.close>=r.open else "#d62728"
        a.plot([i,i],[r.low,r.high],color=col,lw=.7)
        a.plot([i,i],[r.open,r.close],color=col,lw=2.4,solid_capstyle="butt")
    a.axvline(off-0.5,color="#111",lw=1.6)
    a.axvline(off+trth_start-0.5,color="#888",lw=1.0,ls="--")
    a.axhline(e["R"],color="#1f77b4",lw=1.8,label=f"{e['level']} = {e['R']:.2f}")
    a.axvline(off+trth_start+e["brk"],color="#ff7f0e",lw=1.3,ls=":",label="break")
    a.axvline(off+trth_start+e["entry"],color="#111",lw=1.8,label="entry")
    a.text(off/2,a.get_ylim()[1],"PRIOR SESSION\n(defines the level)",ha="center",va="top",fontsize=7,color="#555")
    a.text(off+trth_start+10,a.get_ylim()[1],"trade day",ha="left",va="top",fontsize=7,color="#555")
    a.set_title(f"{e['sym']}  {str(e['date'])[:10]}  {e['level']}-{e['kind']}",fontsize=9)
    a.set_xticks([]); a.tick_params(labelsize=7); a.legend(fontsize=6,loc="lower left")
fig.suptitle("Where the level comes from and how it is acted on.  Black line = session boundary, "
             "grey dashed = 09:30, blue = the level, orange = break, black = retest entry",fontsize=11)
plt.tight_layout(); os.makedirs("figures",exist_ok=True)
plt.savefig("figures/twoday_context.png",dpi=120,facecolor="white")
print("wrote figures/twoday_context.png")
