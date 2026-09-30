"""EXPLORATORY. Search for rules that reproduce the fingerprint of the posted MT5 curve,
rather than for profit. His clues:
- 3 FX pairs; "super simple, indicator-based"; one parameter
- stops, no pyramiding, flat at the end of each day
- trades bunch in volatile stretches, so the threshold is probably fixed, not
  volatility-scaled

Families (15-minute closes; FX day = 17:00-17:00 New York; entries to 15:00; flat at 16:45):
  open  fade a move of more than x% from the day's first price     -> target the day's open
  sma   fade a close more than x% from its 20-bar hourly SMA        -> target that SMA (fixed at entry)
  bar   fade an hour whose close-to-close move is more than x%      -> target the hour's starting price
The stop is x% beyond the entry. One position per pair.

Score against his curve (2021 on, dates from `plot_vs_theirs.py`):
  timing : correlation of log trade rate with his, across his date-label intervals
           (each interval holds the same number of his trades)
  pnl    : correlation of quarterly gross P&L with his quarterly balance change
Null: the best score over all combinations when his intervals and quarters are
shuffled (200 shuffles). Uses dev and holdout data. This is a matching exercise,
not a performance claim.

  HOLDOUT_UNLOCK=final-evaluation python3 explore_fx/match.py
"""
import multiprocessing as mp
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_fx")
import one_rule
from plot_vs_theirs import LABELS

TH = [0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
FAMS = ["open", "sma", "bar"]
TRIPLES = {"EUR, GBP, AUD vs USD": ("E6", "B6", "A6"), "EUR, GBP, JPY vs USD": ("E6", "B6", "J1"),
           "EUR, AUD, NZD vs USD": ("E6", "A6", "N6"), "EUR, GBP, CHF vs USD": ("E6", "B6", "E1"),
           "AUD, NZD, JPY vs USD": ("A6", "N6", "J1"), "crosses EURGBP, AUDNZD, EURCHF": ("EURGBP", "AUDNZD", "EURCHF")}
PX = {}


def m15():
    d = {s: pd.concat([one_rule.load("dev")[s], one_rule.load("holdout")[s]]).close for s in one_rule.TICK}
    out = {s: c.resample("15min", label="right", closed="right").last().dropna() for s, c in d.items()}
    for name, (a, b) in {"EURGBP": ("E6", "B6"), "AUDNZD": ("A6", "N6"), "EURCHF": ("E6", "E1")}.items():
        out[name] = (out[a] / out[b]).dropna()
    return out


def sim(job):
    sym, fam, x = job
    c = PX[sym]
    ts, P = c.index, c.values
    session = (ts + pd.Timedelta("7h")).normalize()
    tod = ts.hour * 60 + ts.minute
    if fam == "open":
        ref = pd.Series(P, index=ts).groupby(session).transform("first").values
    elif fam == "sma":
        h = c.resample("1h", label="right", closed="right").last().dropna()
        ref = h.rolling(20).mean().reindex(ts, method="ffill").values
    else:
        ref = pd.Series(P, index=ts).shift(4).values
    dist = P / ref - 1
    can_enter = (tod < 15 * 60) | (tod >= 18 * 60)
    flat = (tod >= 16 * 60 + 45) & (tod < 18 * 60)
    X = x / 100
    trades, pos = [], 0
    for i in range(len(P)):
        if pos:
            day_end = flat[i] or session[i] != s_in
            hit_t = pos * (P[i] - tgt) >= 0
            hit_s = pos * (P[i] - stp) <= 0
            if day_end or hit_t or hit_s:
                trades.append((t_in, ts[i], pos * (P[i] / e - 1) * 1e4))
                pos = 0
                continue
        if not pos and can_enter[i] and abs(dist[i]) > X and not np.isnan(dist[i]):
            pos = -int(np.sign(dist[i]))
            e, tgt, t_in, s_in = P[i], ref[i], ts[i], session[i]
            stp = e * (1 - pos * X)
    return job, pd.DataFrame(trades, columns=["t_in", "t_out", "bp"])


def fingerprint(t, iv, his_q):
    days = np.array([(b - a).days for a, b in iv])
    cnt = np.array([((t.t_in >= a) & (t.t_in < b)).sum() for a, b in iv])
    q = t.groupby(t.t_out.dt.to_period("Q")).bp.sum()
    j = pd.concat([his_q, q], axis=1).dropna()
    return np.log(cnt / days + 1e-3), j.iloc[:, 0].values, j.iloc[:, 1].values


if __name__ == "__main__":
    PX.update(m15())
    jobs = [(s, f, x) for s in PX for f in FAMS for x in TH]
    with mp.get_context("fork").Pool(12) as pool:
        res = dict(pool.map(sim, jobs))
    lab = pd.to_datetime(LABELS, format="%Y.%m.%d")
    iv = [(lab[i], lab[i + 1]) for i in range(len(lab) - 1) if lab[i] >= pd.Timestamp("2021-01-11")]
    his_rate = np.log(1 / np.array([(b - a).days for a, b in iv]))
    th = pd.read_csv("explore_fx/figures/their_curve_digitised.csv", parse_dates=["date"]).set_index("date").balance
    his_q = th.resample("QE").last().diff()
    his_q.index = his_q.index.to_period("Q")
    his_q = his_q[his_q.index >= pd.Period("2021Q1")]
    rows, fps = [], []
    for tname, syms in TRIPLES.items():
        for f in FAMS:
            for x in TH:
                t = pd.concat([res[(s, f, x)] for s in syms])
                if len(t) < 50:
                    continue
                rate, hq, oq = fingerprint(t, iv, his_q)
                fps.append((rate, hq, oq))
                per_yr = t.groupby(t.t_in.dt.year).bp.sum()
                rows.append(dict(pairs=tname, family=f, x_pct=x, trades=len(t), win=(t.bp > 0).mean(),
                                 gross_bp=t.bp.mean(), timing=np.corrcoef(rate, his_rate)[0, 1],
                                 pnl=np.corrcoef(hq, oq)[0, 1], y2026_bp=per_yr.get(2026, 0) / 100,
                                 hold_h=((t.t_out - t.t_in).dt.total_seconds() / 3600).median()))
    out = pd.DataFrame(rows)
    out["score"] = out.timing + out.pnl
    rng = np.random.default_rng(7)
    null = []
    for _ in range(200):
        pr, pq = rng.permutation(len(his_rate)), rng.permutation(len(fps[0][1]))
        best = max(np.corrcoef(r, his_rate[pr])[0, 1] + np.corrcoef(h[pq[:len(h)] % len(h)], o)[0, 1]
                   for r, h, o in fps)
        null.append(best)
    out.sort_values("score", ascending=False).to_csv("explore_fx/match.csv", index=False, float_format="%.3f")
    pd.set_option("display.width", 220)
    print(out.sort_values("score", ascending=False).head(15).round(2).to_string(index=False))
    print(f"\n{len(out)} combinations. Best score by chance (shuffled): median {np.median(null):.2f}, "
          f"95th pct {np.percentile(null, 95):.2f}. Best real: {out.score.max():.2f}")
