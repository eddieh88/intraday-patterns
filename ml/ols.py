"""Amendment 5 of prereg/opening_ml.md: monotonicity check, then OLS on the top drivers.
Development only; post-hoc, so the holdout decides.

  python3 ml/ols.py
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from paths import add_to_path
add_to_path("ml")
import walk

FEATS = ["atr_pct", "tod1", "tod5", "r_prev_oc"]
RHO_MIN = 0.8


def deciles(T, f):
    d = T[[f, "y", "date"]].dropna()
    d = d.assign(dec=np.clip(np.floor((d[f] + 0.5) * 10), 0, 9).astype(int))
    return d.groupby("dec").y.mean() * 1e4


def fit(tr, cols):
    X = sm.add_constant(tr[cols].fillna(0.0))
    return sm.OLS(tr.t_rank, X).fit(cov_type="cluster", cov_kwds={"groups": tr.date.factorize()[0]})


def main():
    T = walk.load()
    pd.set_option("display.width", 200)
    print("STEP 1  monotonicity: mean y (bp) by decile of the day rank, all development\n")
    keep = []
    for f in FEATS:
        m = deciles(T, f)
        rho = stats.spearmanr(m.index, m.values)[0]
        flips = int((np.diff(np.sign(np.diff(m.values))) != 0).sum())
        by_year = {y: deciles(g, f) for y, g in T.groupby(T.date.dt.year)}
        mono = abs(rho) >= RHO_MIN
        keep += [f] if mono else []
        print(f"  {f:10s} rho {rho:+.2f}  direction changes {flips}  {'MONOTONIC' if mono else 'not monotonic -> dropped'}")
        print("     all:  " + " ".join(f"{v:+5.1f}" for v in m.values))
        for y, v in by_year.items():
            print(f"     {y}: " + " ".join(f"{x:+5.1f}" for x in v.values))
    print(f"\nfeatures kept: {keep}")
    if not keep:
        return

    T["vol_x_es"] = T.atr_pct * T.m_ES_open / T.m_ES_open.std()
    print("\nSTEP 2  OLS walk-forward")
    for name, cols in (("M1", keep), ("M2", keep + ["vol_x_es"])):
        preds, coefs = [], []
        for b, (s, e) in enumerate(walk.BLOCKS):
            tr, va, te = walk.split(T, s, e)
            tr = pd.concat([tr, va])                      # OLS needs no validation set
            r = fit(tr, cols)
            preds.append(te.assign(p=r.predict(sm.add_constant(te[cols].fillna(0.0), has_constant="add")), block=b))
            coefs.append({c: (r.params[c], r.tvalues[c]) for c in cols})
        P = pd.concat(preds)
        ic, sp = walk.daily_ic(P, "p"), walk.spread(P, "p")
        n6 = sp - walk.COST["net6"]
        icb = P.assign(_v=P.date.map(ic)).groupby("block")._v.mean()
        n6b = P.assign(_v=P.date.map(n6)).groupby("block")._v.mean()
        ok = n6.mean() > 0 and walk.tstat(n6) >= 2.75 and (n6b > 0).sum() >= 5
        print(f"\n{name} {cols}")
        print(f"  IC {ic.mean():+.4f} (t {walk.tstat(ic):+.2f}), blocks+ {(icb > 0).sum()}/7: " + " ".join(f"{v:+.3f}" for v in icb))
        print(f"  spread {sp.mean() * 1e4:+.2f} bp/day (t {walk.tstat(sp):+.2f}); net 6bp {n6.mean() * 1e4:+.2f} (t {walk.tstat(n6):+.2f}), "
              f"blocks+ {(n6b > 0).sum()}/7: " + " ".join(f"{v * 1e4:+.1f}" for v in n6b))
        print("  coefficients by fold (x100, clustered t):")
        for c in cols:
            print(f"    {c:10s} " + "  ".join(f"{co[c][0] * 100:+.2f}({co[c][1]:+.1f})" for co in coefs))
        print(f"  VERDICT (development, post-hoc): {'PASS -> holdout' if ok else 'fail'}")


if __name__ == "__main__":
    main()
