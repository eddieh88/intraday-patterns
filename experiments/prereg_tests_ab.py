"""Tests A and B, exactly as pre-registered in PREREG_intraday.md."""
import glob, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")

ERAS = (("2002-2008", 2002, 2008), ("2009-2016", 2009, 2016), ("2017-2026", 2017, 2026))
dvr = pd.read_parquet("cache/mp_dv.parquet").rolling(21, min_periods=10).mean()
eps = pd.read_parquet("cache/mp_eps_K5_N900.parquet")

files = sorted(glob.glob("cache/mp5/*.parquet"))
print(f"{len(files)} sample days\n")

rowsA, rowsB = [], []
for p in files:
    d = pd.read_parquet(p)
    d["t"] = pd.to_datetime(d["timestamp"])
    day = d["t"].dt.normalize().iloc[0]
    if day not in dvr.index: continue
    univ = dvr.loc[day].dropna().nlargest(900).index
    d["sym"] = d["symbol"].astype(str).str.replace("-DELISTED","",regex=False).str.upper()
    d = d[d.sym.isin(set(univ))]
    if not len(d): continue
    tm = d["t"].dt.hour*60 + d["t"].dt.minute
    # hazard: exclude name-days with too few bars, and skip the opening auction
    reg = d[(tm >= 575) & (tm <= 960)]                     # 09:35 .. 16:00
    cnt = reg.groupby("sym").size()
    keep = set(cnt[cnt >= 40].index)                       # 5-min bars: 40 of ~77
    reg = reg[reg.sym.isin(keep)]
    if reg.sym.nunique() < 100: continue
    g = reg.sort_values("t").groupby("sym")
    first = g["close"].first()
    noon  = reg[tm.reindex(reg.index) <= 720].sort_values("t").groupby("sym")["close"].last()
    p1545 = reg[tm.reindex(reg.index) <= 945].sort_values("t").groupby("sym")["close"].last()
    last  = g["close"].last()
    common = first.index.intersection(noon.index).intersection(last.index)
    if len(common) < 100: continue
    am = (noon[common]/first[common] - 1)
    pm = (last[common]/noon[common] - 1)
    am = am - am.mean(); pm = pm - pm.mean()               # cross-sectionally demeaned
    ok = np.isfinite(am) & np.isfinite(pm) & (am.abs() < 0.5) & (pm.abs() < 0.5)
    if ok.sum() >= 100:
        rowsB.append((day, float(np.corrcoef(am[ok], pm[ok])[0,1]), int(ok.sum())))
    rowsA.append((day, p1545[common], last[common]))

B = pd.DataFrame(rowsB, columns=["day","corr","n"]).set_index("day")
print("=== TEST B: does a morning residual predict afternoon reversal? ===")
print("(cross-sectionally demeaned, 09:35-12:00 vs 12:00-16:00, split at noon)\n")
print("{:>12s} {:>10s} {:>8s} {:>10s}".format("era","mean corr","days","median n"))
print("-"*44)
vals = {}
for lab, y0, y1 in ERAS:
    s = B[(B.index.year >= y0) & (B.index.year <= y1)]
    if not len(s): continue
    vals[lab] = s["corr"].mean()
    print("{:>12s} {:+10.4f} {:8d} {:10.0f}".format(lab, s["corr"].mean(), len(s), s["n"].median()))
m, base = vals.get("2017-2026"), vals.get("2002-2008")
if m is not None and base is not None:
    if m < -0.010 and m < base: v = "MOVED INTRADAY"
    elif abs(m) <= 0.005 or m > base: v = "NOT INTRADAY"
    else: v = "AMBIGUOUS"
    print(f"\n  2017-2026 {m:+.4f}  vs  2002-2008 {base:+.4f}")
    print(f"  VERDICT: {v}")

print("\n=== TEST A: how much signal is lost between 15:45 and the close? ===")
px = pd.read_parquet("cache/mp_close.parquet")
ratio = []
for day, p45, cl in rowsA:
    c = px.loc[day].reindex(p45.index)
    r = (cl/p45 - 1)
    ok = np.isfinite(r) & (r.abs() < 0.2)
    if ok.sum() >= 100: ratio.append((day, float(r[ok].std()), float(cl[ok].std()/cl[ok].mean())))
R = pd.DataFrame(ratio, columns=["day","last15_vol","x"]).set_index("day")
print("{:>12s} {:>16s}".format("era","last 15min move"))
print("-"*30)
for lab, y0, y1 in ERAS:
    s = R[(R.index.year >= y0) & (R.index.year <= y1)]
    if len(s): print("{:>12s} {:15.3f}%".format(lab, s["last15_vol"].mean()*100))
print("\n(cross-sectional SD of the 15:45->close move: what a close-signal sees")
print(" and a 15:45-signal cannot. Compare to daily residual vol ~2.08%.)")
