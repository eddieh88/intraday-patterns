"""Walk-forward for the opening-hour ML study (prereg/opening_ml.md, Amendments 1-3).

  python3 ml/walk.py       development: model, baselines, drivers, distilled rule, verdicts
  python3 ml/walk.py drivers    the Amendment 2 analyses (time and regime heterogeneity)

Writes cache/ml_walk_preds.parquet (out-of-sample predictions) and
cache/ml_walk_drivers.parquet (|SHAP| and single-feature IC by fold).
"""
import sys, warnings

import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy import stats
from sklearn.linear_model import Ridge

from holdout import assert_sealed

warnings.filterwarnings("ignore", category=UserWarning)

STOCK = ["r_or", "r_or1", "r_or2", "or_rng_atr", "or_vol_rel", "or_pos", "vwap_dev", "rel_or",
         "gap", "pre_ret", "pre_dv_rel", "tod1", "tod5", "tod20", "r_prev", "r_prev_oc", "r_prev_last",
         "r5", "r20", "d_pdh", "d_pdl", "open_pos", "atr_ratio", "atr_pct", "log_price", "pool_rank",
         "log_dv20", "mx_ES", "mx_ZN", "mx_DX", "mx_CL", "mx_VX", "sec_rel_or", "sec_vs_spy"]
CONTEXT = ["mkt_or", "mkt_atr", "m_ES", "m_ZN", "m_DX", "m_J1", "m_CL", "m_GC", "m_VX", "m_BTC",
           "m_ES_open", "m_NQ_ES", "m_RTY_ES", "m_curve", "m_ES_rv20", "dow"]
FEATS = STOCK + CONTEXT
BLOCKS = [("2022-01-01", "2022-07-01"), ("2022-07-01", "2023-01-01"), ("2023-01-01", "2023-07-01"),
          ("2023-07-01", "2024-01-01"), ("2024-01-01", "2024-07-01"), ("2024-07-01", "2025-01-01"),
          ("2025-01-01", "2025-04-01")]
GAP, VALID = 5, 0.15
PARAMS = dict(objective="regression", num_leaves=15, learning_rate=0.03, min_data_in_leaf=500,
              feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0,
              seed=7, verbose=-1, num_threads=12)
ALPHAS = [1, 10, 100, 1_000, 10_000]
COST = {"net6": 6e-4, "net12": 12e-4}          # per day, dollar-neutral spread (3 / 6 bp per stock)


def load(period="dev"):
    T = pd.read_parquet(f"cache/ml_open_{period}.parquet")
    T = T[np.isfinite(T.r_target)].copy()
    assert_sealed(T.date) if period == "dev" else None
    T["y"] = T.r_target - T.groupby("date").r_target.transform("mean")
    T["t_rank"] = T.groupby("date").y.rank(pct=True) - 0.5
    for f in STOCK:                                       # cross-sectional ranks within each day
        T[f] = T.groupby("date")[f].rank(pct=True) - 0.5
    return T.sort_values(["date", "symbol"]).reset_index(drop=True)


def daily_ic(df, col):
    g = df.groupby("date")
    ic = g.apply(lambda d: stats.spearmanr(d[col], d.y, nan_policy="omit")[0] if d[col].notna().sum() > 10 else np.nan)
    return ic.dropna()


def spread(df, col):
    """Long the top fifth, short the bottom fifth, per day: mean raw return difference."""
    def one(d):
        d = d[d[col].notna()]
        if len(d) < 20:
            return np.nan
        q = d[col].rank(pct=True)
        return d.r_target[q > 0.8].mean() - d.r_target[q <= 0.2].mean()
    return df.groupby("date").apply(one).dropna()


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def split(T, start, end):
    sess = np.array(sorted(T.date.unique()))
    s0 = np.searchsorted(sess, np.datetime64(start))
    train_s = sess[:max(0, s0 - GAP)]
    nv = int(len(train_s) * VALID)
    tr, va = set(train_s[:-nv]), set(train_s[-nv:])
    te = T[(T.date >= start) & (T.date < end)]
    return T[T.date.isin(tr)], T[T.date.isin(va)], te


def fit_lgb(tr, va):
    dtr = lgb.Dataset(tr[FEATS], tr.t_rank)
    dva = lgb.Dataset(va[FEATS], va.t_rank, reference=dtr)
    return lgb.train(PARAMS, dtr, 1000, valid_sets=[dva], callbacks=[lgb.early_stopping(50, verbose=False)])


def fit_ridge(tr, va):
    mu, sd = tr[FEATS].mean(), tr[FEATS].std().replace(0, 1)
    z = lambda d: ((d[FEATS] - mu) / sd).fillna(0).values
    best = None
    for a in ALPHAS:
        m = Ridge(alpha=a).fit(z(tr), tr.t_rank)
        err = np.mean((m.predict(z(va)) - va.t_rank) ** 2)
        best = min(best, (err, a, m), key=lambda x: x[0]) if best else (err, a, m)
    return (lambda d: best[2].predict(z(d))), best[1]


def main():
    T = load()
    print(f"{len(T):,} name-days, {T.date.nunique()} sessions, {len(FEATS)} features "
          f"({len(STOCK)} ranked, {len(CONTEXT)} context)\n")
    preds, drivers = [], []
    for b, (s, e) in enumerate(BLOCKS):
        tr, va, te = split(T, s, e)
        m = fit_lgb(tr, va)
        rp, alpha = fit_ridge(tr, va)
        te = te.assign(p_lgb=m.predict(te[FEATS], num_iteration=m.best_iteration), p_ridge=rp(te),
                       p_b1=te.rel_or, block=b)
        shap = m.predict(te[FEATS], num_iteration=m.best_iteration, pred_contrib=True)[:, :-1]
        imp = pd.Series(np.abs(shap).mean(0), index=FEATS)
        tr_ic = {f: daily_ic(tr.assign(_f=tr[f]), "_f").mean() for f in STOCK}
        te_ic = {f: daily_ic(te.assign(_f=te[f]), "_f").mean() for f in STOCK}
        for f in FEATS:
            drivers.append(dict(block=b, feature=f, shap=imp[f], train_ic=tr_ic.get(f, np.nan), test_ic=te_ic.get(f, np.nan)))
        print(f"block {b} {s}..{e}: train {tr.date.nunique()} + valid {va.date.nunique()} sessions, "
              f"test {te.date.nunique()}; trees {m.best_iteration}; ridge alpha {alpha}")
        preds.append(te)
    P = pd.concat(preds)
    D = pd.DataFrame(drivers)
    P.to_parquet("cache/ml_walk_preds.parquet", index=False)
    D.to_parquet("cache/ml_walk_drivers.parquet", index=False)

    # ---- the model, the baselines ----
    print("\nOUT OF SAMPLE (7 blocks pooled)")
    print(f"{'':10s}{'IC':>9s}{'t':>7s}{'blocks+':>9s}{'spread bp':>11s}{'t':>7s}{'net6':>8s}{'t':>7s}{'net12':>8s}{'blocks+ net6':>14s}")
    res = {}
    for col, name in (("p_lgb", "LightGBM"), ("p_ridge", "ridge"), ("p_b1", "B1 mom")):
        ic = daily_ic(P, col)
        sp = spread(P, col)
        n6, n12 = sp - COST["net6"], sp - COST["net12"]
        icb = P.assign(_ic=P.date.map(ic)).groupby("block")._ic.mean()
        n6b = P.assign(_s=P.date.map(n6)).groupby("block")._s.mean()
        res[col] = dict(ic=ic, sp=sp, n6=n6, icb=icb, n6b=n6b)
        print(f"{name:10s}{ic.mean():+9.4f}{tstat(ic):+7.2f}{(icb > 0).sum():>6d}/7{sp.mean() * 1e4:+11.2f}{tstat(sp):+7.2f}"
              f"{n6.mean() * 1e4:+8.2f}{tstat(n6):+7.2f}{n12.mean() * 1e4:+8.2f}{(n6b > 0).sum():>11d}/7")
    print("\nIC by block:      " + "  ".join(f"{b}:{v:+.3f}" for b, v in res["p_lgb"]["icb"].items()))
    print("net6 bp by block: " + "  ".join(f"{b}:{v * 1e4:+.1f}" for b, v in res["p_lgb"]["n6b"].items()))
    L, B1 = res["p_lgb"], res["p_b1"]
    d = (L["ic"] - B1["ic"].reindex(L["ic"].index)).dropna()
    sig = L["ic"].mean() > 0 and tstat(L["ic"]) >= 3.0 and (L["icb"] > 0).sum() >= 5 and tstat(d) >= 2.0
    pays = L["n6"].mean() > 0 and tstat(L["n6"]) >= 2.75 and (L["n6b"] > 0).sum() >= 5
    print(f"\nLightGBM IC - B1 IC: {d.mean():+.4f} (t {tstat(d):+.2f})")
    print(f"VERDICT  model has signal: {'PASS' if sig else 'fail'}   model strategy pays: {'PASS' if pays else 'fail'}")

    # ---- drivers ----
    D["rank"] = D.groupby("block").shap.rank(ascending=False)
    top = D[D["rank"] <= 5].groupby("feature").size().sort_values(ascending=False)
    meanimp = D.groupby("feature").shap.mean().sort_values(ascending=False)
    print("\nDRIVERS: mean |SHAP| (x1e3) and folds in the top 5")
    for f in meanimp.index[:15]:
        icb = D[D.feature == f].set_index("block").test_ic
        print(f"  {f:12s} {meanimp[f] * 1e3:7.3f}   top5 in {top.get(f, 0)}/7   test IC by block: "
              + " ".join(f"{v:+.3f}" if np.isfinite(v) else "  n/a " for v in icb))

    # ---- distilled rule ----
    stable = [f for f in meanimp.index if top.get(f, 0) >= 5 and f in STOCK][:3]
    print(f"\nDISTILLED RULE from stable drivers: {stable if stable else 'none qualify'}")
    if stable:
        parts = []
        for b in range(len(BLOCKS)):
            sgn = D[(D.block == b) & D.feature.isin(stable)].set_index("feature").train_ic.apply(np.sign)
            te = P[P.block == b]
            parts.append(te.assign(p_rule=sum(sgn[f] * te[f] for f in stable) / len(stable)))
        R = pd.concat(parts)
        ic, sp = daily_ic(R, "p_rule"), spread(R, "p_rule")
        n6 = sp - COST["net6"]
        n6b = R.assign(_s=R.date.map(n6)).groupby("block")._s.mean()
        ok = n6.mean() > 0 and tstat(n6) >= 2.75 and (n6b > 0).sum() >= 5
        print(f"  IC {ic.mean():+.4f} (t {tstat(ic):+.2f})  spread {sp.mean() * 1e4:+.2f} bp (t {tstat(sp):+.2f})  "
              f"net6 {n6.mean() * 1e4:+.2f} bp (t {tstat(n6):+.2f})  blocks+ {(n6b > 0).sum()}/7")
        print(f"VERDICT  distilled rule pays: {'PASS' if ok else 'fail'}")


if __name__ == "__main__":
    main()
