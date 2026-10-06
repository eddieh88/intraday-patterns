"""Nested hyperparameter search, Amendment 4 of prereg/opening_ml.md (development only).

Per fold: every setting is trained on the training sessions; its tree count and the
setting itself are chosen by daily IC on the validation sessions; only the chosen
model is scored on the test block.

  python3 ml/tune.py      -> cache/ml_tune.parquet and a printed verdict
"""
import itertools, json, os, time, warnings
os.environ.setdefault("OMP_NUM_THREADS", "1")              # one thread per worker, prediction included
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb

from paths import add_to_path
add_to_path("ml")
import walk

warnings.filterwarnings("ignore")
GRID = [dict(num_leaves=nl, min_data_in_leaf=md, lambda_l2=l2, learning_rate=lr, objective=ob)
        for nl, md, l2, lr, ob in itertools.product((4, 15, 63), (100, 500, 2000), (0.0, 1.0, 10.0),
                                                     (0.01, 0.03, 0.1), ("regression", "lambdarank"))]
MAX_TREES, EVERY = 1000, 10
T = None
PARTS = Path("cache/ml_tune_parts")                        # one file per finished fit, so a rerun resumes


def daily_ic(df, pred):
    """Mean daily Spearman between pred and y (rank both within each date)."""
    d = pd.DataFrame({"date": df.date.values, "y": df.y.values, "p": pred})
    d["ry"] = d.groupby("date").y.rank(); d["rp"] = d.groupby("date").p.rank()
    c = d.groupby("date")[["ry", "rp"]].corr().unstack().iloc[:, 1]
    return c.mean(), c


def init():
    global T
    T = walk.load()


def one(job):
    b, g = job
    s, e = walk.BLOCKS[b]
    tr, va, te = walk.split(T, s, e)
    params = dict(feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, seed=7, verbose=-1,
                  num_threads=1, **{k: v for k, v in GRID[g].items()})
    if params["objective"] == "lambdarank":
        lab = tr.groupby("date").y.rank(pct=True).mul(5).clip(upper=4.999).astype(int)
        ds = lgb.Dataset(tr[walk.FEATS], lab, group=tr.groupby("date", sort=False).size().values)
        params.update(label_gain=list(range(5)), lambdarank_truncation_level=100)
    else:
        ds = lgb.Dataset(tr[walk.FEATS], tr.t_rank)
    m = lgb.train(params, ds, MAX_TREES)
    best_k, best_v = EVERY, -np.inf
    for k in range(EVERY, MAX_TREES + 1, EVERY):
        v, _ = daily_ic(va, m.predict(va[walk.FEATS], num_iteration=k, num_threads=1))
        if v > best_v:
            best_k, best_v = k, v
    t_ic, _ = daily_ic(te, m.predict(te[walk.FEATS], num_iteration=best_k, num_threads=1))
    out = dict(block=b, setting=g, trees=best_k, valid_ic=best_v, test_ic=t_ic)
    (PARTS / f"{b}_{g}.json").write_text(json.dumps(out))
    return out


def main():
    t0 = time.time()
    PARTS.mkdir(parents=True, exist_ok=True)
    jobs = [(b, g) for b in range(len(walk.BLOCKS)) for g in range(len(GRID))
            if not (PARTS / f"{b}_{g}.json").exists()]
    print(f"{len(jobs)} fits to run ({len(walk.BLOCKS) * len(GRID) - len(jobs)} already saved)", flush=True)
    if jobs:
        with ProcessPoolExecutor(12, initializer=init) as ex:     # a dead worker raises instead of hanging
            futs = [ex.submit(one, j) for j in jobs]
            for i, f in enumerate(as_completed(futs), 1):
                f.result()
                if i % 50 == 0 or i == len(jobs):
                    print(f"  {i}/{len(jobs)} fits  {time.time() - t0:.0f}s", flush=True)
    R = pd.DataFrame([json.loads(p.read_text()) for p in PARTS.glob("*.json")])
    R.to_parquet("cache/ml_tune.parquet", index=False)
    print(f"{len(R):,} fits ({len(GRID)} settings x {len(walk.BLOCKS)} folds), {time.time() - t0:.0f}s\n")

    # nested choice: best validation IC per fold, then retrain it to score the test block day by day
    chosen = R.loc[R.groupby("block").valid_ic.idxmax()].sort_values("block")
    init()
    preds = []
    for r in chosen.itertuples():
        s, e = walk.BLOCKS[r.block]
        tr, va, te = walk.split(T, s, e)
        params = dict(feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, seed=7, verbose=-1,
                      num_threads=12, **GRID[r.setting])
        if params["objective"] == "lambdarank":
            lab = tr.groupby("date").y.rank(pct=True).mul(5).clip(upper=4.999).astype(int)
            ds = lgb.Dataset(tr[walk.FEATS], lab, group=tr.groupby("date", sort=False).size().values)
            params.update(label_gain=list(range(5)), lambdarank_truncation_level=100)
        else:
            ds = lgb.Dataset(tr[walk.FEATS], tr.t_rank)
        m = lgb.train(params, ds, int(r.trees))
        preds.append(te.assign(p=m.predict(te[walk.FEATS]), block=r.block))
        g = GRID[r.setting]
        print(f"block {r.block}: leaves {g['num_leaves']}, min_data {g['min_data_in_leaf']}, l2 {g['lambda_l2']}, "
              f"lr {g['learning_rate']}, {g['objective']}, {r.trees} trees | valid IC {r.valid_ic:+.4f}, test IC {r.test_ic:+.4f}")
    P = pd.concat(preds)
    ic = walk.daily_ic(P, "p"); sp = walk.spread(P, "p"); n6 = sp - walk.COST["net6"]
    icb = P.assign(_v=P.date.map(ic)).groupby("block")._v.mean()
    n6b = P.assign(_v=P.date.map(n6)).groupby("block")._v.mean()
    b1 = walk.daily_ic(P, "rel_or"); d = (ic - b1.reindex(ic.index)).dropna()
    sig = ic.mean() > 0 and walk.tstat(ic) >= 3 and (icb > 0).sum() >= 5 and walk.tstat(d) >= 2
    pays = n6.mean() > 0 and walk.tstat(n6) >= 2.75 and (n6b > 0).sum() >= 5
    print(f"\nNESTED-TUNED MODEL, out of sample: IC {ic.mean():+.4f} (t {walk.tstat(ic):+.2f}), blocks+ {(icb > 0).sum()}/7, "
          f"vs B1 {d.mean():+.4f} (t {walk.tstat(d):+.2f})")
    print(f"  spread {sp.mean() * 1e4:+.2f} bp/day (t {walk.tstat(sp):+.2f}); net 6bp {n6.mean() * 1e4:+.2f} (t {walk.tstat(n6):+.2f}), blocks+ {(n6b > 0).sum()}/7")
    print(f"VERDICT  signal: {'PASS' if sig else 'fail'}   pays: {'PASS' if pays else 'fail'}")

    # information only: how much do the settings matter on the test blocks?
    avg = R.groupby("setting")[["valid_ic", "test_ic"]].mean()
    avg = avg.join(pd.DataFrame(GRID)).sort_values("test_ic", ascending=False)
    print("\n(information only) test IC averaged over folds: best, median, worst settings")
    pd.set_option("display.width", 200)
    print(pd.concat([avg.head(5), avg.iloc[[len(avg) // 2]], avg.tail(3)]).round(4).to_string())
    print(f"\ncorrelation across settings, mean valid IC vs mean test IC: {avg.valid_ic.corr(avg.test_ic):+.2f}")


if __name__ == "__main__":
    main()
