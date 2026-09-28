"""Amendment 4 of prereg/selection.md: the one pre-specified nonlinear model.

Identical to step3.py except for the model. Settings are fixed in the amendment
and never tuned on test blocks; the number of trees comes from early stopping
on each training set's own last six months, then the model is refit on the
full training set with that many trees.

  python3 selection/step3_lgbm.py   -> cache/sel_oos_lgbm.parquet
"""
import pandas as pd, numpy as np, sys, warnings
import lightgbm as lgb
import statsmodels.api as sm
from scipy.stats import spearmanr
from paths import add_to_path
add_to_path("selection")
from step3 import load, clip_t, BLOCKS, PURGE
warnings.filterwarnings("ignore")

PARAMS = dict(objective="regression", max_depth=3, num_leaves=7, learning_rate=0.02,
              min_child_samples=500, colsample_bytree=0.8, subsample=0.8, subsample_freq=1,
              reg_lambda=10.0, random_state=0, n_jobs=8, verbose=-1)
CAP, PATIENCE = 2000, 100

def fit_predict(train, test, feats, target):
    cut = train.date.max() - pd.DateOffset(months=6)
    inner, val = train[train.date <= cut], train[train.date > cut]
    yi, yv = clip_t(inner, val, target)
    m = lgb.LGBMRegressor(n_estimators=CAP, **PARAMS)
    m.fit(inner[feats], yi, eval_set=[(val[feats], yv)], callbacks=[lgb.early_stopping(PATIENCE, verbose=False)])
    n_trees = max(1, m.best_iteration_ or CAP)
    ytr, yte = clip_t(train, test, target)
    final = lgb.LGBMRegressor(n_estimators=n_trees, **PARAMS).fit(train[feats], ytr)
    return final.predict(test[feats]), ytr, yte, n_trees, pd.Series(final.booster_.feature_importance("gain"), index=feats)

def main():
    D, feats = load()
    dates = np.array(sorted(D.date.unique()))
    out = {}
    for target in ("y", "er"):
        preds, rows, imps = [], [], []
        for s, e in zip(BLOCKS[:-1], BLOCKS[1:]):
            s, e = pd.Timestamp(s), pd.Timestamp(e)
            train = D[D.date <= dates[dates < s][-1 - PURGE]]
            test = D[(D.date >= s) & (D.date < e)]
            p, ytr, yte, n_trees, imp = fit_predict(train, test, feats, target)
            imps.append(imp / imp.sum() if imp.sum() > 0 else imp)
            sse, sst = ((yte - p) ** 2).sum(), ((yte - ytr.mean()) ** 2).sum()
            rows.append(dict(block=f"{s:%Y-%m}", n=len(test), trees=n_trees, r2=1 - sse / sst,
                             spearman=spearmanr(p, yte).statistic))
            preds.append(pd.DataFrame({"date": test.date.values, "symbol": test.symbol.values,
                                       "pred": p, "actual": yte, "sst_part": (yte - ytr.mean()) ** 2}))
        P = pd.concat(preds, ignore_index=True)
        r2 = 1 - ((P.actual - P.pred) ** 2).sum() / P.sst_part.sum()
        ols = sm.OLS(P.actual, sm.add_constant(P.pred)).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(P.date)[0]})
        out[target] = (P, pd.DataFrame(rows), r2, spearmanr(P.pred, P.actual).statistic,
                       ols.params["pred"], ols.tvalues["pred"], pd.concat(imps, axis=1).mean(axis=1))
    for target, label in (("y", "SIGNED CONTINUATION"), ("er", "EFFICIENCY RATIO")):
        P, blocks, r2, rho, slope, t, imp = out[target]
        print(f"\n=== LightGBM, {label}: {len(P):,} name-days, {P.date.nunique()} sessions")
        print(f"  pooled R^2 {r2:+.4f}   Spearman {rho:+.4f}   slope {slope:+.3f} (session-clustered t {t:+.2f})")
        print(blocks.to_string(index=False, float_format=lambda v: f"{v:+.4f}"))
        print("  share of split gain, mean over folds:  " +
              ",  ".join(f"{k} {v:.0%}" for k, v in imp.sort_values(ascending=False).head(8).items()))
    out["y"][0][["date","symbol","pred"]].to_parquet("cache/sel_oos_lgbm.parquet", index=False)
    print("\n-> cache/sel_oos_lgbm.parquet")

if __name__ == "__main__":
    main()
