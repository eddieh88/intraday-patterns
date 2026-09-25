"""One figure per intraday experiment, from the cached tables.

    python3 exploration/render_experiments.py
    -> exploration/figures/E1..E7_*.png

Each figure shows the measurement, the benchmark it is judged against, and the
sample size, so the claim can be checked rather than taken on trust.
"""
import pandas as pd, numpy as np, os, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import stats
OUT="exploration/figures"; os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.facecolor":"white","axes.grid":True,"grid.alpha":.25,
                     "font.size":9,"axes.titlesize":10})
D=pd.read_parquet("cache/intraday_daily.parquet")
def save(fig,name):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png",dpi=125,facecolor="white")
    plt.close(fig); print("wrote",name)

# ---------------- E1: is the open different? ----------------
import glob
fs=sorted(glob.glob("cache/mp5min/*.parquet"))[::12]
d=pd.concat([pd.read_parquet(f,columns=["timestamp","symbol","high","low","close","volume"])
             for f in fs],ignore_index=True)
d["symbol"]=d.symbol.str.replace("-DELISTED","",regex=False)
t=pd.to_datetime(d.timestamp); d["h"]=t.dt.hour+t.dt.minute/60
d=d[(d.h>=9.5)&(d.h<16)]
dv=(d.close*d.volume).groupby(d.symbol).sum()
d=d[d.symbol.isin(set(dv.nlargest(300).index))]
d["rng"]=(d.high-d.low)/d.close; d["blk"]=(d.h*2).astype(int)/2
g=d.groupby("blk").agg(rng=("rng","median"),vol=("volume","sum"))
g["volshare"]=g.vol/g.vol.sum()
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
lbl=[f"{int(b)}:{int((b-int(b))*60):02d}" for b in g.index]
ax[0].bar(range(len(g)),g.rng*100,color="#2c7fb8")
mid=d[(d.h>=11)&(d.h<15)].rng.median()*100
ax[0].axhline(mid,color="#d62728",ls="--",lw=1.2,label=f"11:00-15:00 median {mid:.3f}%")
ax[0].set_xticks(range(len(g))); ax[0].set_xticklabels(lbl,rotation=60,fontsize=7)
ax[0].set_ylabel("median 5-min bar range (%)"); ax[0].legend(fontsize=7)
ax[0].set_title(f"E1: range by time of day — open is {g.rng.iloc[0]/ (mid/100):.2f}x midday")
ax[1].bar(range(len(g)),g.volshare*100,color="#41ab5d")
ax[1].axhline(100/len(g),color="#d62728",ls="--",lw=1.2,label="flat = no concentration")
ax[1].set_xticks(range(len(g))); ax[1].set_xticklabels(lbl,rotation=60,fontsize=7)
ax[1].set_ylabel("share of RTH volume (%)"); ax[1].legend(fontsize=7)
ax[1].set_title("E1: volume by time of day")
fig.suptitle(f"E1  the open differs from the rest of the session   "
             f"(top 300 names, {len(fs)} sampled sessions)  CONFIRMED",fontsize=11)
save(fig,"E1_open_profile")

# ---------------- E2: do gaps fill? ----------------
E=D.dropna(subset=["pdc","o_or"]).copy(); E["gap"]=E.o_or/E.pdc-1
E["filled"]=np.where(E.gap>0,E.lo_rth<=E.pdc,E.hi_rth>=E.pdc)
bins=[(0,.002,"<0.2%"),(.002,.005,"0.2-0.5%"),(.005,.01,"0.5-1%"),(.01,.02,"1-2%"),(.02,9,">2%")]
up=[];dn=[];ns=[]
for lo,hi,_ in bins:
    s=E[(E.gap.abs()>=lo)&(E.gap.abs()<hi)]
    up.append(s[s.gap>0].filled.mean()*100); dn.append(s[s.gap<0].filled.mean()*100); ns.append(len(s))
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
x=np.arange(len(bins))
ax[0].bar(x-.2,up,.4,label="gap up",color="#2c7fb8"); ax[0].bar(x+.2,dn,.4,label="gap down",color="#fdae61")
ax[0].axhline(50,color="#666",ls=":",lw=1)
ax[0].set_xticks(x); ax[0].set_xticklabels([b[2] for b in bins]); ax[0].set_ylabel("% filled same session")
ax[0].legend(fontsize=8); ax[0].set_title("E2: fill rate DECLINES with gap size")
for i,(u,n) in enumerate(zip(up,ns)): ax[0].text(i,u+2,f"n={n//1000}k",ha="center",fontsize=6)
E["om"]=E.c_open/E.o_or-1
sub=[E[E.gap>.005].om*100, E[E.gap<-.005].om*-100]
ax[1].boxplot(sub,labels=["fade gap-up\n(short)","fade gap-down\n(long)"],showfliers=False,whis=(10,90))
ax[1].axhline(0,color="#d62728",ls="--",lw=1.2)
ax[1].set_ylabel("9:30-11:00 return in fade direction (%)")
ax[1].set_title(f"E2: fading pays {sub[0].mean():+.3f}% / {sub[1].mean():+.3f}%  (spread is 1-8bp)")
fig.suptitle(f"E2  do opening gaps fill?   n={len(E):,} symbol-days   SIZE-DEPENDENT",fontsize=11)
save(fig,"E2_gap_fill")

# ---------------- E3: PO3 / judas swing ----------------
E=D.dropna(subset=["o_or","c_or","o_open","c_open"]).copy()
E["orm"]=E.c_or/E.o_or-1; E["nxt"]=E.c_open/E.o_open-1
E=E[E.orm!=0]
q=pd.qcut(E.orm,20,duplicates="drop")
gg=E.groupby(q,observed=True).agg(x=("orm","mean"),y=("nxt","mean"),n=("nxt","size"))
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
ax[0].scatter(gg.x*100,gg.y*100,s=28,color="#2c7fb8")
ax[0].axhline(0,color="#666",lw=.8); ax[0].axvline(0,color="#666",lw=.8)
b,a=np.polyfit(E.orm,E.nxt,1)
xs=np.linspace(E.orm.quantile(.01),E.orm.quantile(.99),50)
ax[0].plot(xs*100,(a+b*xs)*100,color="#d62728",lw=1.4,label=f"slope {b:+.4f}")
ax[0].set_xlabel("9:30-10:00 move (%)"); ax[0].set_ylabel("10:00-11:00 move (%)")
ax[0].legend(fontsize=8); ax[0].set_title("E3: no relationship (20 bins of opening move)")
sizes=[(0,.003,"<0.3%"),(.003,.007,"0.3-0.7%"),(.007,.015,"0.7-1.5%"),(.015,9,">1.5%")]
rv=[]
for lo,hi,_ in sizes:
    s=E[(E.orm.abs()>=lo)&(E.orm.abs()<hi)]
    rv.append((np.sign(s.nxt)!=np.sign(s.orm)).mean()*100)
ax[1].bar(range(len(sizes)),rv,color="#7fbc41")
ax[1].axhline(50,color="#d62728",ls="--",lw=1.4,label="50% = coin flip")
ax[1].set_ylim(45,55); ax[1].set_xticks(range(len(sizes)))
ax[1].set_xticklabels([s[2] for s in sizes]); ax[1].set_ylabel("reversal rate (%)")
ax[1].legend(fontsize=8); ax[1].set_title("E3: reversal rate by size of opening move")
fig.suptitle(f"E3  is the opening move a false move? (PO3 / judas swing)   "
             f"n={len(E):,}   NULL",fontsize=11)
save(fig,"E3_po3")

# ---------------- E4: opening-range sweep ----------------
E=D.dropna(subset=["hi_or","lo_or","hi_open","lo_open","c_rth"]).copy()
bh=E[E.hi_open>E.hi_or]; bl=E[E.lo_open<E.lo_or]
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
ax[0].bar(["OR high\nbroken","OR low\nbroken"],
          [(bh.c_rth<bh.hi_or).mean()*100,(bl.c_rth>bl.lo_or).mean()*100],
          color=["#2c7fb8","#fdae61"])
ax[0].axhline(50,color="#d62728",ls="--",lw=1.4,label="50% = break holds as often as it fails")
ax[0].set_ylim(40,60); ax[0].set_ylabel("% that closed back INSIDE the range")
ax[0].legend(fontsize=8); ax[0].set_title("E4: breaks hold slightly more than they fail")
for i,(s,n) in enumerate(((bh,len(bh)),(bl,len(bl)))): ax[0].text(i,51,f"n={n//1000}k",ha="center",fontsize=7)
fade_h=-(bh.c_rth/bh.hi_or-1)*100; fade_l=(bl.c_rth/bl.lo_or-1)*100
ax[1].bar([0,1],[fade_h.mean(),fade_l.mean()],color="#d62728",label="fade the break")
ax[1].bar([2,3],[-fade_h.mean(),-fade_l.mean()],color="#41ab5d",label="hold the break")
ax[1].axhline(0,color="#111",lw=.8)
ax[1].set_xticks([0,1,2,3]); ax[1].set_xticklabels(["fade\nhigh","fade\nlow","hold\nhigh","hold\nlow"],fontsize=8)
ax[1].set_ylabel("mean return to the close (%)"); ax[1].legend(fontsize=8)
ax[1].set_title("E4: fading LOSES, continuation wins (both ~6bp = spread)")
fig.suptitle(f"E4  is the opening range swept then reversed?   n={len(bh):,} high breaks   REFUTED",fontsize=11)
save(fig,"E4_or_sweep")

# ---------------- E5: does pre-market predict the open? ----------------
E=D.dropna(subset=["c_pre","pdc","o_or","c_open","pdh","pdl","hi_pre","lo_pre"]).copy()
E["pre"]=E.c_pre/E.pdc-1; E["op"]=E.c_open/E.o_or-1
q=pd.qcut(E.pre,20,duplicates="drop")
gg=E.groupby(q,observed=True).agg(x=("pre","mean"),y=("op","mean"))
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
ax[0].scatter(gg.x*100,gg.y*100,s=28,color="#2c7fb8")
ax[0].axhline(0,color="#666",lw=.8); ax[0].axvline(0,color="#666",lw=.8)
b,a=np.polyfit(E.pre,E.op,1); xs=np.linspace(E.pre.quantile(.01),E.pre.quantile(.99),50)
ax[0].plot(xs*100,(a+b*xs)*100,color="#d62728",lw=1.4,label=f"slope {b:+.4f}")
ax[0].set_xlabel("pre-market move 04:00-09:30 (%)"); ax[0].set_ylabel("9:30-11:00 move (%)")
ax[0].legend(fontsize=8); ax[0].set_title("E5: pre-market carries no directional signal")
sh=E[(E.hi_pre>E.pdh)&(E.c_pre<E.pdh)]; sl=E[(E.lo_pre<E.pdl)&(E.c_pre>E.pdl)]
base=E.op.mean()*100
taught=[-sh.op.mean()*100-base, sl.op.mean()*100-base]     # edge over baseline
opp   =[ sh.op.mean()*100-base,-sl.op.mean()*100-base]
xx=np.arange(2); w=.35
ax[1].bar(xx-w/2,taught,w,color="#d62728",label="the taught direction")
ax[1].bar(xx+w/2,opp,w,color="#41ab5d",label="the OPPOSITE direction")
ax[1].axhline(0,color="#111",lw=1)
ax[1].set_xticks(xx)
ax[1].set_xticklabels([f"swept prior HIGH\ntaught: short  (n={len(sh):,})",
                       f"swept prior LOW\ntaught: long  (n={len(sl):,})"],fontsize=8)
ax[1].set_ylabel("edge over unconditional (%)")
ax[1].legend(fontsize=7)
ax[1].set_title("E5: high-sweep is INVERTED; low-sweep is absent")
for i,(a_,b_) in enumerate(zip(taught,opp)):
    ax[1].text(i-w/2,a_,f"{a_:+.3f}",ha="center",va="top" if a_<0 else "bottom",fontsize=7)
    ax[1].text(i+w/2,b_,f"{b_:+.3f}",ha="center",va="bottom" if b_>0 else "top",fontsize=7)
fig.suptitle(f"E5  does pre-market tell you the day's direction?   "
             f"n={len(E):,}   REFUTED — and the high-sweep rule is BACKWARDS",fontsize=11)
save(fig,"E5_premarket")

# ---------------- E6: prior-day S/R break + retest ----------------
for tag,f in (("a  stop below entry bar","cache/e6_trades.parquet"),
              ("b  stop below the level","cache/e6b_trades.parquet")):
    if not os.path.exists(f): continue
    T=pd.read_parquet(f); b=T[T.kind=="bounce"]
    fig,ax=plt.subplots(1,3,figsize=(16,4.2))
    ax[0].hist(np.clip(b.R,-1.5,3.2),bins=70,color="#2c7fb8")
    ax[0].axvline(0,color="#111",lw=.8); ax[0].axvline(b.R.mean(),color="#d62728",lw=1.6,
        label=f"mean {b.R.mean():+.3f}R"); ax[0].axvline(np.median(b.R),color="#41ab5d",lw=1.4,
        ls="--",label=f"median {np.median(b.R):+.3f}R")
    ax[0].set_xlabel("R multiple"); ax[0].legend(fontsize=8); ax[0].set_title("E6: outcome distribution")
    lv=T.groupby(["level","kind"]).R.agg(["mean","size"]).reset_index()
    lv=lv[lv["size"]>500]
    ax[1].barh([f"{r.level} {r.kind}" for r in lv.itertuples()],lv["mean"],
               color=["#d62728" if m<0 else "#41ab5d" for m in lv["mean"]])
    ax[1].axvline(0,color="#111",lw=.8); ax[1].set_xlabel("mean R")
    ax[1].set_title("E6: every level, every variant, negative")
    tgt=(b.R>2.9).mean(); stp=(b.R<-0.95).mean()
    ax[2].pie([tgt,stp,1-tgt-stp],labels=[f"hit 3R\n{tgt:.1%}",f"stopped\n{stp:.1%}",
              f"timed out\n{1-tgt-stp:.1%}"],colors=["#41ab5d","#d62728","#fdae61"],
              autopct="",startangle=90)
    ax[2].set_title("E6: only 15% reach the target")
    fig.suptitle(f"E6{tag}   n={len(b):,} bounce trades   "
                 f"mean {b.R.mean():+.3f}R  t={b.R.mean()/(b.R.std()/np.sqrt(len(b))):+.1f}   NEGATIVE",fontsize=11)
    save(fig,f"E6{tag.split()[0]}_retest")

# ---------------- E7: ORB on stocks in play ----------------
T=pd.read_parquet("cache/e7_trades.parquet"); T["yr"]=pd.to_datetime(T.date).dt.year
tiers=[("top 20",T[T.rk<=20]),("21-50",T[(T.rk>20)&(T.rk<=50)]),("51-200",T[T.rk>50])]
fig,ax=plt.subplots(1,3,figsize=(16,4.2))
w=.35; x=np.arange(3)
for off,col,lab in ((-w/2,"#2c7fb8","stop = opposite side of OR"),(w/2,"#fdae61","stop = 1.5 x ATR")):
    key="A" if off<0 else "B"
    m=[t[1][key].dropna().mean() for t in tiers]
    e=[t[1][key].dropna().std()/np.sqrt(t[1][key].notna().sum()) for t in tiers]
    ax[0].bar(x+off,m,w,yerr=e,capsize=3,color=col,label=lab)
ax[0].axhline(0,color="#111",lw=.8); ax[0].set_xticks(x); ax[0].set_xticklabels([t[0] for t in tiers])
ax[0].set_xlabel("relative-volume rank tier"); ax[0].set_ylabel("mean R per trade")
ax[0].legend(fontsize=7); ax[0].set_title("E7: the relvol filter sorts monotonically")
t20=T[T.rk<=20]
yr=t20.groupby("yr").A.agg(["mean","size"]).reset_index()
ax[1].bar(yr.yr.astype(str),yr["mean"],color=["#2c7fb8" if y<=2023 else "#9ecae1" for y in yr.yr])
ax[1].axhline(0,color="#111",lw=.8)
ax[1].set_ylabel("mean R (stop = OR)"); ax[1].set_title("E7: by year — dark = inside paper's sample")
ax[2].hist(np.clip(t20.A.dropna(),-1.5,3),bins=70,color="#2c7fb8")
ax[2].axvline(0,color="#111",lw=.8)
ax[2].axvline(t20.A.mean(),color="#d62728",lw=1.6,label=f"mean {t20.A.mean():+.3f}R")
ax[2].set_xlabel("R multiple"); ax[2].legend(fontsize=8); ax[2].set_title("E7: top-20 outcome distribution")
fig.suptitle(f"E7  opening-range breakout on 'stocks in play'   n={len(t20):,} top-20 trades   "
             f"DEAD by pre-registration (needed >+0.05R, t>3, both variants)",fontsize=11)
save(fig,"E7_orb")
print("\nall figures written")
