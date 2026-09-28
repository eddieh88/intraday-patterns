"""Step 3 of prereg/selection.md: descriptive ridge regressions. No verdict.

Two targets, fitted separately:
  y   signed continuation -- does the opening direction persist?
  er  efficiency ratio    -- is it a trend day, in either direction?

Walk-forward over development: six test blocks from 2022-07 to 2025-03, each
trained on everything before it less a 2-session purge. Inside each training
set the ridge penalty is chosen on its last six months, then refit on all of it.
Winsorising and standardising use training data only. The three registered
interactions are products of standardised features.

Writes the out-of-sample predictions of y, which step 4 ranks on.

  python3 selection/step3.py   -> cache/sel_oos.parquet
"""
import pandas as pd, numpy as np, sys
import statsmodels.api as sm
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from holdout import assert_sealed

BLOCKS = ["2022-07-01","2023-01-01","2023-07-01","2024-01-01","2024-07-01","2025-01-01","2025-04-01"]
ALPHAS = [1, 10, 100, 1_000, 10_000]
PURGE = 2
INTERACT = [("gap","spy_aligned"), ("or15_relvol","spy_aligned"), ("room_R","signal_size")]

def load():
    F = pd.read_parquet("cache/sel_features.parquet"); O = pd.read_parquet("cache/sel_outcomes.parquet")
    D = F.merge(O, on=["date","symbol"])
    for k in range(1, 5): D[f"dow_{k}"] = (D.dow == k).astype(float)
    feats = [c for c in F.columns if c not in ("date","symbol","side","R_bp","dow")] + [f"dow_{k}" for k in range(1,5)]
    n = len(D); D = D.dropna(subset=feats + ["y","er"])
    print(f"{n:,} name-days with outcomes; {len(D):,} complete cases ({n-len(D):,} dropped for a missing feature)")
    assert_sealed(D.date)
    return D, feats

def prep(train, test, feats):
    """winsorise and standardise on train; add interactions; same transform on test."""
    lo, hi = train[feats].quantile(.01), train[feats].quantile(.99)
    tr, te = train[feats].clip(lo, hi, axis=1), test[feats].clip(lo, hi, axis=1)
    mu, sd = tr.mean(), tr.std().replace(0, 1)
    tr, te = (tr - mu) / sd, (te - mu) / sd
    for a, b in INTERACT:
        tr[f"{a}*{b}"] = tr[a] * tr[b]; te[f"{a}*{b}"] = te[a] * te[b]
    return tr.values, te.values, list(tr.columns)

def clip_t(train, test, col):
    lo, hi = train[col].quantile(.01), train[col].quantile(.99)
    return train[col].clip(lo, hi).values, test[col].clip(lo, hi).values

def fit(train, feats, target):
    """choose alpha on the last six months of train, then refit on all of train."""
    cut = train.date.max() - pd.DateOffset(months=6)
    inner, val = train[train.date <= cut], train[train.date > cut]
    Xi, Xv, _ = prep(inner, val, feats); yi, yv = clip_t(inner, val, target)
    score = {a: -np.mean((Ridge(alpha=a).fit(Xi, yi).predict(Xv) - yv) ** 2) for a in ALPHAS}
    alpha = max(score, key=score.get)
    return alpha

def main():
    D, feats = load()
    dates = np.array(sorted(D.date.unique()))
    oos, report = [], {}
    for target in ("y", "er"):
        preds, coefs, rows = [], [], []
        for s, e in zip(BLOCKS[:-1], BLOCKS[1:]):
            s, e = pd.Timestamp(s), pd.Timestamp(e)
            before = dates[dates < s]
            train = D[D.date <= before[-1 - PURGE]]
            test = D[(D.date >= s) & (D.date < e)]
            alpha = fit(train, feats, target)
            Xtr, Xte, names = prep(train, test, feats)
            ytr, yte = clip_t(train, test, target)
            m = Ridge(alpha=alpha).fit(Xtr, ytr); p = m.predict(Xte)
            coefs.append(pd.Series(m.coef_, index=names))
            sse, sst = ((yte - p) ** 2).sum(), ((yte - ytr.mean()) ** 2).sum()
            rows.append(dict(block=f"{s:%Y-%m}", n=len(test), alpha=alpha, r2=1 - sse / sst,
                             spearman=spearmanr(p, yte).statistic))
            preds.append(pd.DataFrame({"date": test.date.values, "symbol": test.symbol.values,
                                       "pred": p, "actual": yte, "sst_part": (yte - ytr.mean()) ** 2}))
        P = pd.concat(preds, ignore_index=True)
        r2 = 1 - ((P.actual - P.pred) ** 2).sum() / P.sst_part.sum()
        ols = sm.OLS(P.actual, sm.add_constant(P.pred)).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(P.date)[0]})
        C = pd.concat(coefs, axis=1)
        report[target] = (pd.DataFrame(rows), r2, spearmanr(P.pred, P.actual).statistic,
                          ols.params["pred"], ols.tvalues["pred"], C, len(P), P.date.nunique())
        if target == "y":
            oos = P[["date","symbol","pred"]]

    for target, label in (("y", "SIGNED CONTINUATION (does the opening direction persist?)"),
                          ("er", "EFFICIENCY RATIO (is it a trend day, either direction?)")):
        blocks, r2, rho, slope, t, C, n, ns = report[target]
        print(f"\n=== {label}")
        print(f"out-of-sample: {n:,} name-days, {ns} sessions")
        print(f"  pooled R^2 {r2:+.4f}   Spearman {rho:+.4f}   slope of outcome on prediction {slope:+.3f} (session-clustered t {t:+.2f})")
        print(blocks.to_string(index=False, float_format=lambda v: f"{v:+.4f}"))
        mean = C.mean(axis=1); agree = (np.sign(C).eq(np.sign(mean), axis=0)).sum(axis=1)
        top = mean.abs().sort_values(ascending=False).index[:12]
        print(f"  largest standardised coefficients (mean over {C.shape[1]} folds; folds agreeing on sign):")
        for k in top: print(f"    {k:28s}{mean[k]:+.4f}   {agree[k]}/{C.shape[1]}")

    oos.to_parquet("cache/sel_oos.parquet", index=False)
    print(f"\n-> cache/sel_oos.parquet ({len(oos):,} out-of-sample predictions of y, for step 4)")

if __name__ == "__main__":
    main()
