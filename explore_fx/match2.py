"""EXPLORATORY. Second search for the posted FX strategy, using his own descriptions
(kieranduff.com): "no negatively skewed strategies", "minimum 1:1 risk-to-reward",
"one bullet in the chamber", fixed stops, flat daily, standard lookbacks. Also his
worked example: "if Friday is bearish, buy the open, 1:1 with a fixed stop".

Every rule here uses a fixed stop of s% and a target of rr x s% (rr >= 1), one
position per pair per day, flat at 16:45 New York. The FX day starts 18:00 New York.
Within a bar the stop is checked before the target.

  prevday  if the previous FX day moved more than x% (open to close), fade it at the
           next day's first bar
  asia     at 03:00 New York (London open), fade the move since 18:00 if > x%
  fix      at 11:05 New York (after the 16:00 London fix), fade the 08:00-11:00 move if > x%
  gap      at the Sunday reopen, fade the weekend gap from Friday's last price if > x%
  friday   his S&P rule in FX: at the Sunday reopen, fade Friday's session (open to close) if > x%
  bb       an hourly close outside Bollinger(20, 2): fade at the next bar (max one a day)
  rsi      an hourly RSI(20) below 30 / above 70: fade at the next bar (max one a day)

Scoring against his curve is the same as match.py (timing across his date-label
intervals, quarterly P&L), with a shuffled-null baseline. His own bar for a passing
strategy is also reported: Sharpe 1-2, max drawdown 4-12%, 200+ trades.

  HOLDOUT_UNLOCK=final-evaluation python3 explore_fx/match2.py
"""
import multiprocessing as mp
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_fx")
import one_rule
from match import TRIPLES
from plot_vs_theirs import LABELS

COST = {"E6": 0.6, "B6": 0.8, "A6": 0.9, "J1": 0.7, "N6": 1.2, "E1": 1.0,
        "EURGBP": 0.75, "AUDNZD": 1.6, "EURCHF": 0.75}          # bp round trip, ECN-like
GRID = {"prevday": [0.0, 0.3, 0.6], "asia": [0.0, 0.2, 0.4], "fix": [0.0, 0.15, 0.3],
        "gap": [0.05, 0.15, 0.3], "friday": [0.0, 0.2, 0.4], "bb": [None], "rsi": [None]}
STOPS, RRS = [0.2, 0.4], [1.0, 2.0]
BARS = {}


def load5():
    d = {s: pd.concat([one_rule.load("dev")[s], one_rule.load("holdout")[s]]) for s in one_rule.TICK}
    out = {s: m[~m.index.duplicated()] for s, m in d.items()}
    for name, (a, b) in {"EURGBP": ("E6", "B6"), "AUDNZD": ("A6", "N6"), "EURCHF": ("E6", "E1")}.items():
        c = (out[a].close / out[b].close).dropna()
        out[name] = pd.DataFrame({"open": c.shift().fillna(c), "high": c, "low": c, "close": c})
    return out


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def entries(b, fam, x):
    """-> list of (bar position to enter at its open, side)"""
    ts = b.index
    session = (ts + pd.Timedelta("6h")).normalize()
    tod = ts.hour * 60 + ts.minute
    O, C = b.open.values, b.close.values
    out = []
    if fam in ("prevday", "gap", "friday"):
        first = pd.Series(np.arange(len(ts)), index=ts).groupby(session).first()
        last = pd.Series(np.arange(len(ts)), index=ts).groupby(session).last()
        for k in range(1, len(first)):
            i, p0, p1 = first.iloc[k], first.iloc[k - 1], last.iloc[k - 1]
            if fam == "prevday":
                move = C[p1] / O[p0] - 1
            elif fam == "friday":
                if ts[i].dayofweek != 6:
                    continue
                move = C[p1] / O[p0] - 1
            else:
                if ts[i].dayofweek != 6:
                    continue
                move = O[i] / C[p1] - 1
            if abs(move) > x / 100:
                out.append((i, -int(np.sign(move))))
        return out
    if fam in ("asia", "fix"):
        t_ent, t_from = (180, 18 * 60) if fam == "asia" else (11 * 60 + 5, 8 * 60)
        s = pd.Series(np.arange(len(ts)), index=ts)
        for sess, g in s.groupby(session):
            gt = tod[g.values]
            ent = g.values[gt >= t_ent] if fam == "fix" else g.values[(gt >= t_ent) & (gt < 17 * 60)]
            frm = g.values[(gt >= t_from)] if fam == "fix" else g.values[gt >= t_from]
            if not len(ent) or not len(frm):
                continue
            i, j = ent[0], frm[0]
            if j >= i:
                continue
            move = C[i - 1] / O[j] - 1
            if abs(move) > x / 100:
                out.append((i, -int(np.sign(move))))
        return out
    h = b.close.resample("1h", label="right", closed="right").last().dropna()
    if fam == "bb":
        m, sd = h.rolling(20).mean(), h.rolling(20).std()
        sig = np.sign((h < m - 2 * sd).astype(int) - (h > m + 2 * sd).astype(int))
    else:
        r = rsi(h, 20)
        sig = np.sign((r < 30).astype(int) - (r > 70).astype(int))
    sig = sig[sig != 0]
    pos = ts.searchsorted(sig.index)
    seen = set()
    for p, sd_ in zip(pos, sig.values):
        if p >= len(ts) or tod[p] >= 16 * 60 + 30 and tod[p] < 18 * 60:
            continue
        if session[p] in seen:
            continue
        seen.add(session[p])
        out.append((p, int(sd_)))
    return out


def run_bracket(b, ents, s, rr):
    ts = b.index
    session = (ts + pd.Timedelta("6h")).normalize().values
    tod = ts.hour * 60 + ts.minute
    O, H, L = b.open.values, b.high.values, b.low.values
    trades = []
    for i, side in ents:
        e = O[i]
        stop, tgt = e * (1 - side * s / 100), e * (1 + side * rr * s / 100)
        j = i
        while j < len(ts):
            if session[j] != session[i] or (16 * 60 + 45 <= tod[j] < 18 * 60):
                px = O[j]; break
            if (L[j] <= stop) if side == 1 else (H[j] >= stop):
                px = stop; break
            if (H[j] >= tgt) if side == 1 else (L[j] <= tgt):
                px = tgt; break
            j += 1
        else:
            continue
        trades.append((ts[i], ts[min(j, len(ts) - 1)], side * (px / e - 1) * 1e4))
    return pd.DataFrame(trades, columns=["t_in", "t_out", "bp"])


def job(args):
    sym, fam, x, s, rr = args
    b = BARS[sym]
    t = run_bracket(b, entries(b, fam, x), s, rr)
    t["net"] = t.bp - COST[sym]
    return args, t


if __name__ == "__main__":
    BARS.update(load5())
    jobs = [(sym, f, x, s, rr) for sym in BARS for f, xs in GRID.items() for x in xs for s in STOPS for rr in RRS]
    with mp.get_context("fork").Pool(14) as pool:
        res = dict(pool.map(job, jobs))
    lab = pd.to_datetime(LABELS, format="%Y.%m.%d")
    iv = [(lab[i], lab[i + 1]) for i in range(len(lab) - 1) if lab[i] >= pd.Timestamp("2021-01-11")]
    days = np.array([(b - a).days for a, b in iv])
    his_rate = np.log(1 / days)
    th = pd.read_csv("explore_fx/figures/their_curve_digitised.csv", parse_dates=["date"]).set_index("date").balance
    his_q = th.resample("QE").last().diff()
    his_q.index = his_q.index.to_period("Q")
    his_q = his_q[his_q.index >= pd.Period("2021Q1")]
    rows, fps = [], []
    bdays = pd.date_range("2021-01-03", "2026-09-20", freq="D")     # calendar days: Sunday exits count
    for tname, syms in TRIPLES.items():
        for f, xs in GRID.items():
            for x in xs:
                for s in STOPS:
                    for rr in RRS:
                        t = pd.concat([res[(sym, f, x, s, rr)] for sym in syms])
                        if len(t) < 60:
                            continue
                        cnt = np.array([((t.t_in >= a) & (t.t_in < b)).sum() for a, b in iv])
                        rate = np.log(cnt / days + 1e-3)
                        q = t.groupby(t.t_out.dt.to_period("Q")).net.sum()
                        j = pd.concat([his_q, q], axis=1).dropna()
                        fps.append((rate, j.iloc[:, 0].values, j.iloc[:, 1].values))
                        d = t.groupby(t.t_out.dt.normalize()).net.sum().reindex(bdays, fill_value=0) / 3
                        eq = d.cumsum()
                        dd = (eq.cummax() - eq).max()
                        rows.append(dict(pairs=tname, family=f, x=x, stop=s, rr=rr, trades=len(t),
                                         win=(t.net > 0).mean(), net_bp=t.net.mean(),
                                         sharpe=d.mean() / d.std() * np.sqrt(365) if d.std() else 0,
                                         ret_dd=eq.iloc[-1] / dd if dd else 0,
                                         y2026=t[t.t_in.dt.year == 2026].net.sum(),
                                         timing=np.corrcoef(rate, his_rate)[0, 1] if rate.std() else 0,
                                         pnl=np.corrcoef(j.iloc[:, 0], j.iloc[:, 1])[0, 1]))
    out = pd.DataFrame(rows).fillna(0)
    out["score"] = out.timing + out.pnl
    rng = np.random.default_rng(7)
    null = []
    for _ in range(200):
        pr, pq = rng.permutation(len(his_rate)), rng.permutation(len(his_q))
        best = -9
        for r, hq, oq in fps:
            a = np.corrcoef(r, his_rate[pr])[0, 1] if r.std() else 0
            b_ = np.corrcoef(hq[pq[:len(hq)] % len(hq)], oq)[0, 1]
            best = max(best, a + b_)
        null.append(best)
    out = out.sort_values("score", ascending=False)
    out.to_csv("explore_fx/match2.csv", index=False, float_format="%.3f")
    pd.set_option("display.width", 240)
    print(out.head(15).round(2).to_string(index=False))
    print(f"\n{len(out)} combinations. Best score by chance (shuffled): median {np.median(null):.2f}, "
          f"95th pct {np.percentile(null, 95):.2f}. Best real: {out.score.max():.2f}")
    good = out[(out.sharpe >= 1) & (out.trades >= 200)]
    print(f"\nPass his own bar (net Sharpe >= 1, 200+ trades): {len(good)} of {len(out)}")
    print(good.sort_values("sharpe", ascending=False).head(10).round(2).to_string(index=False))
