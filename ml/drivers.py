"""Do the drivers change? Amendment 2 of prereg/opening_ml.md (development only).

  1. over time: each feature's daily IC by block; Cochran's Q across the 7 blocks
  2. by regime, labelled before the fact: volatility thirds (ES 20-session realized
     volatility, cut at the prior 250 sessions' terciles), ES 20-session trend
     up/down, ZN 20-session move up/down; Q across the groups
  4. LightGBM's own pairwise SHAP interactions, top pairs by fold (no verdict)

Part 3 (does regime switching help, out of sample) runs only for features that pass
1 or 2, and is printed as a pointer if so.

  python3 ml/drivers.py
"""
import glob

import numpy as np
import pandas as pd
from scipy import stats

from paths import add_to_path
add_to_path("ml")
import walk

DAY = lambda f: pd.Timestamp(f.split("_")[-1][:10])


def daily_ics(T, f):
    return T.groupby("date").apply(lambda d: stats.spearmanr(d[f], d.y, nan_policy="omit")[0]
                                   if d[f].notna().sum() > 10 else np.nan).dropna()


def cochran(groups):
    """groups: list of arrays of daily ICs -> (Q, df, p, I2, means)."""
    m = np.array([g.mean() for g in groups]); se = np.array([g.std(ddof=1) / np.sqrt(len(g)) for g in groups])
    w = 1 / se ** 2
    mbar = (w * m).sum() / w.sum()
    Q = (w * (m - mbar) ** 2).sum(); df = len(groups) - 1
    return Q, df, stats.chi2.sf(Q, df), max(0.0, (Q - df) / Q) if Q > 0 else 0.0, m


def es_zn_daily(dates):
    """ES and ZN closes at the last bar <= 15:59 of each session, from the 1-minute futures."""
    files = {DAY(f): f for f in glob.glob("cache/mp_futures_1min/*.parquet")}
    rows = []
    for d in dates:
        f = files.get(d)
        if f is None:
            continue
        x = pd.read_parquet(f, columns=["timestamp", "symbol", "close"], filters=[("symbol", "in", ["ES", "ZN"])])
        t = pd.to_datetime(x.timestamp); x = x[(t.dt.hour + t.dt.minute / 60) <= 15 + 59 / 60]
        last = x.sort_values("timestamp").groupby("symbol").close.last()
        rows.append(dict(date=d, ES=last.get("ES", np.nan), ZN=last.get("ZN", np.nan)))
    return pd.DataFrame(rows).set_index("date")


def regimes(T):
    days = pd.Series(sorted(T.date.unique()))
    rv = T.groupby("date").m_ES_rv20.first()
    lab = pd.DataFrame(index=days)
    # volatility thirds: cut at terciles of the prior 250 sessions (expanding until 250)
    vol = []
    for i, d in enumerate(days):
        past = rv.iloc[max(0, i - 250):i].dropna()
        if len(past) < 60 or not np.isfinite(rv.get(d, np.nan)):
            vol.append(np.nan); continue
        lo, hi = np.quantile(past, [1 / 3, 2 / 3])
        vol.append(0 if rv[d] <= lo else (2 if rv[d] > hi else 1))
    lab["vol"] = vol
    px = es_zn_daily(list(days))
    prior = px.shift(1)                                   # known at the prior close
    up = lambda x: np.where(x.isna(), np.nan, np.where(x > 0, 1.0, -1.0))   # a zero move counts as "not up"
    lab["trend"] = up(prior.ES / prior.ES.shift(20) - 1)
    lab["rates"] = up(prior.ZN - prior.ZN.shift(20))
    return lab


def main():
    T = walk.load()
    T = T[T.date >= walk.BLOCKS[0][0]]                   # the 7 out-of-sample blocks
    blk = pd.Series(np.nan, index=T.index)
    for b, (s, e) in enumerate(walk.BLOCKS):
        blk[(T.date >= s) & (T.date < e)] = b
    T = T.assign(block=blk)
    nf = len(walk.STOCK)
    alpha = 0.05 / nf
    print(f"Part 1, over time: Cochran's Q across 7 blocks, Bonferroni p < {alpha:.4f}\n")
    ics = {f: daily_ics(T, f) for f in walk.STOCK}
    bday = T.groupby("date").block.first()
    rows = []
    for f, ic in ics.items():
        g = [ic[bday.reindex(ic.index) == b].values for b in range(len(walk.BLOCKS))]
        Q, df, p, I2, m = cochran(g)
        rows.append(dict(feature=f, ic=ic.mean(), t=walk.tstat(ic), Q=Q, p=p, I2=I2, changes=p < alpha,
                         by_block=" ".join(f"{v:+.3f}" for v in m)))
    R1 = pd.DataFrame(rows).sort_values("p")
    pd.set_option("display.width", 220)
    print(R1.round(4).to_string(index=False))

    print(f"\nPart 2, by regime (labels known before the fact), Bonferroni p < {0.05 / (nf * 3):.5f}\n")
    lab = regimes(T)
    out = []
    for name in ("vol", "trend", "rates"):
        L = lab[name]
        for f, ic in ics.items():
            gl = L.reindex(ic.index)
            g = [ic[gl == v].values for v in sorted(gl.dropna().unique())]
            if len(g) < 2 or min(len(x) for x in g) < 30:
                continue
            Q, df, p, I2, m = cochran(g)
            out.append(dict(regime=name, feature=f, Q=Q, p=p, I2=I2, changes=p < 0.05 / (nf * 3),
                            ic_by_group=" ".join(f"{v:+.3f}" for v in m),
                            n_by_group=" ".join(str(len(x)) for x in g)))
    R2 = pd.DataFrame(out).sort_values("p")
    print(R2.head(15).round(4).to_string(index=False))
    passing = sorted(set(R1[R1.changes].feature) | set(R2[R2.changes].feature))
    print(f"\nfeatures whose effect changes beyond noise: {passing if passing else 'none'}")
    if passing:
        print("-> part 3 (regime switching, out of sample) applies to these")
    R1.to_parquet("cache/ml_drivers_time.parquet", index=False)
    R2.to_parquet("cache/ml_drivers_regime.parquet", index=False)
    lab.to_parquet("cache/ml_regimes.parquet")


if __name__ == "__main__":
    main()
