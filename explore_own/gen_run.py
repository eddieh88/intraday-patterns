"""Run the strategy generator (generator.py) over development spot FX, 2015 on, for the
real data and for shuffled null data. Each strategy runs on all 8 pairs.

  in-sample     2015-01 .. 2020-12   (rank and filter here)
  out-of-sample 2021-01 .. end       (check the survivors here)
Both lie inside development. The 2010-2014 holdout is not touched.

In-sample filter (StrategyQuant-style, set before running):
  >= 300 trades, mean >= +1 bp per trade after costs, monthly Sharpe >= 1.0,
  positive on >= 6 of 8 pairs and >= 5 of 6 years.
The survivors' out-of-sample results are compared with those of the survivors on
shuffled data, which is what the same search finds when there is nothing to find.

  python3 explore_own/gen_run.py [real|null1|null2 ...]  -> cache/own_gen_<tag>.npz
      (append _gross to a tag to trade at the mid, with no costs)
  python3 explore_own/gen_run.py report                  -> summary
  python3 explore_own/gen_run.py persistence             -> does IS rank carry into OOS?
"""
import multiprocessing as mp
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own")
import data
import generator as g

PAIRS = ["eurgbp", "eurchf", "audnzd", "eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]
START = pd.Period("2015-01", "M")
IS_END = pd.Period("2020-12", "M")
P = {}


def build(tag):
    for k, p in enumerate(PAIRS):
        h = g.hourly(data.load(p, "dev"))
        h = h[h.index >= START.start_time]
        if tag.startswith("null"):
            h = g.shuffled(h, seed=int(tag[4]) * 100 + k)
        if tag.endswith("_gross"):                               # no costs: trade at the mid
            for side in ("bid", "ask"):
                for c in ("open", "high", "low", "close"):
                    h[f"{side}_{c}"] = h[f"mid_{c}"]
        sig, fil, atr = g.blocks(h)
        arr = g.prepare(h)
        arr["atr"] = atr
        arr["month"] = np.asarray((h.index.to_period("M") - START).map(lambda x: x.n), np.int64)
        P[p] = (sig, fil, arr)
    return P[PAIRS[0]][0], P[PAIRS[0]][1]


def evaluate(idx):
    cat = CAT
    n_months = int(max(a["month"].max() for _, _, a in P.values())) + 1
    res_m = np.zeros((len(idx), n_months, 3), np.float32)
    res_p = np.zeros((len(idx), len(PAIRS), 2, 2), np.float32)
    split = (IS_END - START).n + 1
    for r, k in enumerate(idx):
        s, rev, f, mode, a, b, hold = cat[k]
        for q, p in enumerate(PAIRS):
            sig, fil, A = P[p]
            lo, sh = sig[s][1], sig[s][2]
            if rev:
                lo, sh = sh, lo
            m = fil[f][1]
            go_l = lo & m if mode in (0, 2) else np.zeros_like(m)
            go_s = sh & m if mode in (1, 2) else np.zeros_like(m)
            out = np.zeros((n_months, 3))
            g.run_one(go_l, go_s, A["atr"], A["bo"], A["bh"], A["bl"], A["bc"], A["ao"], A["ah"], A["al"],
                      A["ac"], A["mid_o"], A["ok"], A["fri_end"], A["month"], a, b, hold, out)
            res_m[r] += out
            res_p[r, q, 0] = out[:split, :2].sum(0)
            res_p[r, q, 1] = out[split:, :2].sum(0)
    return res_m, res_p


def run(tag):
    global CAT
    sig, fil = build(tag)
    CAT = g.catalogue(len(sig), len(fil))
    chunks = np.array_split(np.arange(len(CAT)), 56)
    with mp.get_context("fork").Pool(14) as pool:
        parts = pool.map(evaluate, chunks)
    m = np.concatenate([x[0] for x in parts])
    pp = np.concatenate([x[1] for x in parts])
    names = np.array([f"{sig[s][0]}|{'mom' if rev else 'mr'}|{fil[f][0]}|{g.MODES[md]}|s{a}|t{b}|h{hd}"
                      for s, rev, f, md, a, b, hd in CAT])
    np.savez_compressed(f"cache/own_gen_{tag}.npz", monthly=m, pairs=pp, names=names)
    print(f"{tag}: {len(CAT)} strategies saved")


def metrics(monthly, pairs, sl):
    s, n = monthly[:, sl, 0], monthly[:, sl, 1]
    tot, cnt = s.sum(1), n.sum(1)
    mean = np.divide(tot, cnt, out=np.zeros_like(tot), where=cnt > 0)
    pm = s / len(PAIRS)
    sharpe = np.divide(pm.mean(1), pm.std(1), out=np.zeros_like(tot), where=pm.std(1) > 0) * np.sqrt(12)
    yrs = s.reshape(len(s), -1, 12).sum(2) if s.shape[1] % 12 == 0 else None
    return dict(trades=cnt, bp=mean, sharpe=sharpe, years_up=(yrs > 0).sum(1) if yrs is not None else None)


def report():
    split = (IS_END - START).n + 1
    rows = []
    for tag in ("real", "null1", "null2"):
        try:
            z = np.load(f"cache/own_gen_{tag}.npz")
        except FileNotFoundError:
            continue
        M, Pp, names = z["monthly"], z["pairs"], z["names"]
        ins = metrics(M, Pp, slice(0, split))
        oos = metrics(M, Pp, slice(split, M.shape[1]))
        pairs_up = (Pp[:, :, 0, 0] > 0).sum(1)
        keep = ((ins["trades"] >= 300) & (ins["bp"] >= 1) & (ins["sharpe"] >= 1.0)
                & (pairs_up >= 6) & (ins["years_up"] >= 5))
        k = np.flatnonzero(keep)
        print(f"\n=== {tag}: {len(names)} strategies; {len(k)} pass the in-sample filter ===")
        print(f"all strategies, in-sample Sharpe: 99th pct {np.percentile(ins['sharpe'], 99):.2f}, "
              f"max {ins['sharpe'].max():.2f}")
        if len(k):
            o_sh, o_bp = oos["sharpe"][k], oos["bp"][k]
            print(f"survivors out-of-sample: median Sharpe {np.median(o_sh):+.2f}, "
                  f"share with OOS Sharpe > 0: {np.mean(o_sh > 0):.0%}, > 0.5: {np.mean(o_sh > 0.5):.0%}; "
                  f"median bp/trade {np.median(o_bp):+.2f}")
            top = k[np.argsort(-o_sh)][:15]
            if tag == "real":
                t = pd.DataFrame({"strategy": names[top], "IS_trades": ins["trades"][top].astype(int),
                                  "IS_bp": ins["bp"][top], "IS_sharpe": ins["sharpe"][top],
                                  "OOS_trades": oos["trades"][top].astype(int), "OOS_bp": oos["bp"][top],
                                  "OOS_sharpe": oos["sharpe"][top],
                                  "OOS_pairs_up": (Pp[top, :, 1, 0] > 0).sum(1)})
                pd.set_option("display.width", 250)
                print(t.round(2).to_string(index=False))
        rows.append((tag, len(k)))



def persistence():
    """Does in-sample rank carry into out-of-sample, more on real data than on shuffled?"""
    from scipy.stats import spearmanr
    split = (IS_END - START).n + 1
    for tag in ("real", "null1", "null2", "real_gross", "null1_gross"):
        try:
            z = np.load(f"cache/own_gen_{tag}.npz")
        except FileNotFoundError:
            continue
        M, names = z["monthly"], z["names"]
        ins, oos = metrics(M, None, slice(0, split)), metrics(M, None, slice(split, M.shape[1]))
        ok = ins["trades"] >= 100
        rho = spearmanr(ins["sharpe"][ok], oos["sharpe"][ok]).correlation
        top = ok & (ins["sharpe"] >= np.percentile(ins["sharpe"][ok], 99))
        print(f"{tag}: IS-OOS Sharpe rank corr {rho:+.3f}; top 1% by IS -> OOS median Sharpe "
              f"{np.median(oos['sharpe'][top]):+.2f}, OOS > 0: {np.mean(oos['sharpe'][top] > 0):.0%}")
        # ideas: average over the 60 exit settings
        idea = np.array(["|".join(n.split("|")[:4]) for n in names])
        df = pd.DataFrame({"idea": idea, "is": ins["sharpe"], "oos": oos["sharpe"], "isbp": ins["bp"],
                           "oosbp": oos["bp"], "n": ins["trades"]})
        g_ = df[df.n >= 100].groupby("idea").agg(is_sh=("is", "median"), oos_sh=("oos", "median"),
                                                 is_bp=("isbp", "median"), oos_bp=("oosbp", "median"),
                                                 exits=("is", "size"))
        both = g_[(g_.is_sh > 0) & (g_.oos_sh > 0)]
        print(f"   ideas: {len(g_)}; median-over-exits Sharpe > 0 in both halves: {len(both)} "
              f"({len(both) / len(g_):.1%})")
        if tag.startswith("real"):
            pd.set_option("display.width", 200)
            print(both.sort_values("oos_sh", ascending=False).head(15).round(2).to_string())


if __name__ == "__main__":
    args = sys.argv[1:] or ["real"]
    if args == ["report"]:
        report()
    elif args == ["persistence"]:
        persistence()
    else:
        for tag in args:
            run(tag)
