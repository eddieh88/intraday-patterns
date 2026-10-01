"""EXPLORATORY. A search constrained by the forensics of the posted MT5 chart (explore_fx/
forensics.py and the doc): a weekend-anchored fade with a fixed bracket, scored against all
of his fingerprints at once. Spot FX bid/ask (HistData), 2018-01 .. 2026-07, his chart's span.

Rule template: at an anchor, if a fixed-size move exceeds x%, fade it on each pair; stop s%,
target rr x s% (rr <= 1: his wins never exceed his losses); exit at a fixed time.
  anchors (New York time; broker time = NY + 7h, so a Sunday 17:00 reopen is Monday 00:00):
    gap_w0 / gap_w60     : Sunday reopen (+0 / +60 min), move = weekend gap from Friday's last mid
    fri_w0 / fri_w60     : Sunday reopen (+0 / +60 min), move = Friday's session (Thu 17:00 -> Fri close)
    mon02 / mon03 / mon08: Monday 02:00 / 03:00 / 08:00, move = since the Sunday reopen
  x in {0.1, 0.2, 0.3, 0.5}%, s in {0.15, 0.25, 0.4, 0.6}%, rr in {0.5, 0.75, 1.0},
  exit "day" (Monday 16:45) or "week" (Friday 16:45)
  pairs: every 3 of the 8, equal notional, so a stop costs the same $ on each (his single loss size)

Fingerprints (his, from the chart):
  weekday mix of deal dates (labels: Mon 13, Tue 2, Wed 3, Thu 6, Fri 5) -> multinomial log-likelihood
  trade timing across his label intervals (log rate correlation)
  quarterly P&L correlation with his digitised curve
  win rate of visible steps (57-69%)
  pairs opening together (his margin spikes are almost never a single unit)
  trade count (>= ~450 visible steps)
Entries need the spread filter: <= 3x the pair's median spread and <= its previous-4-minute mean.

  python3 explore_fx/weekend_match.py -> explore_fx/weekend_match.csv
"""
import itertools
import multiprocessing as mp
import numpy as np
import pandas as pd
from numba import njit
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import data
from plot_vs_theirs import LABELS

PAIRS = ["eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy", "eurgbp", "eurchf", "audnzd"]
START, END = pd.Timestamp("2018-01-01"), pd.Timestamp("2026-08-01")
ANCHORS = ["gap_w0", "gap_w60", "fri_w0", "fri_w60", "mon02", "mon03", "mon08"]
XS, SS, RRS, EXITS = (0.1, 0.2, 0.3, 0.5), (0.15, 0.25, 0.4, 0.6), (0.5, 0.75, 1.0), ("day", "week")
HIS_WEEKDAYS = np.array([13, 2, 3, 6, 5])          # Mon..Fri label counts
D = {}


@njit(cache=True)
def walk(t, bo, bh, bl, ao, ah, al, i, side, stop, tgt, t_exit):
    for j in range(i, len(t)):
        if t[j] >= t_exit:
            return j, (bo[j] if side == 1 else ao[j])
        if side == 1:
            if bl[j] <= stop:
                return j, stop
            if j > i and bh[j] >= tgt:
                return j, tgt
        else:
            if ah[j] >= stop:
                return j, stop
            if j > i and al[j] <= tgt:
                return j, tgt
    return -1, 0.0


def prepare(pair):
    d = data.load(pair, "dev")
    d = d[(d.index >= START - pd.Timedelta("7D")) & (d.index < END)]
    sp = d.spread_mean
    ok = (sp <= 3 * sp.median()) & (sp <= sp.shift(1).rolling(4, min_periods=1).mean().fillna(np.inf) + 1e-9)
    A = {k: d[k].values for k in ("bid_open", "bid_high", "bid_low", "ask_open", "ask_high", "ask_low",
                                  "mid_open", "mid_close")}
    A["t"] = d.index.values.astype("int64")
    A["ok"] = ok.values
    A["idx"] = d.index
    return A


def anchors(A):
    """-> {anchor: list of (entry index, move, monday 16:45 ns, friday 16:45 ns)}"""
    idx, ok, mo, mc = A["idx"], A["ok"], A["mid_open"], A["mid_close"]
    out = {a: [] for a in ANCHORS}
    for sun in pd.date_range(START - pd.Timedelta("1D"), END, freq="W-SUN"):
        reopen = sun + pd.Timedelta("17:00:00")
        fri_close = reopen - pd.Timedelta("2D")
        thu_open = fri_close - pd.Timedelta("1D")
        pf = idx.searchsorted(fri_close) - 1
        po = idx.searchsorted(thu_open)
        r0 = idx.searchsorted(reopen)
        if pf < 0 or r0 >= len(idx) or idx[pf] < fri_close - pd.Timedelta("2h") or idx[r0] - reopen > pd.Timedelta("2h"):
            continue
        mon_end = (sun + pd.Timedelta("1D") + pd.Timedelta("16:45:00")).value
        fri_end = (sun + pd.Timedelta("5D") + pd.Timedelta("16:45:00")).value

        def first_ok(t0, limit="2h"):
            i = idx.searchsorted(t0)
            while i < len(idx) and not ok[i] and idx[i] - t0 < pd.Timedelta(limit):
                i += 1
            return i if i < len(idx) and ok[i] and idx[i] - t0 < pd.Timedelta(limit) else None

        for w, tag in ((0, "w0"), (60, "w60")):
            i = first_ok(reopen + pd.Timedelta(minutes=w))
            if i is None:
                continue
            out[f"gap_{tag}"].append((i, mo[i] / mc[pf] - 1, mon_end, fri_end))
            out[f"fri_{tag}"].append((i, mc[pf] / mo[po] - 1, mon_end, fri_end))
        for hh, tag in ((2, "mon02"), (3, "mon03"), (8, "mon08")):
            i = first_ok(sun + pd.Timedelta("1D") + pd.Timedelta(hours=hh))
            if i is None:
                continue
            out[tag].append((i, mo[i] / mo[r0] - 1, mon_end, fri_end))
    return out


def run_pair(pair):
    A = prepare(pair)
    an = anchors(A)
    t = A["t"]
    rows = []
    for a, lst in an.items():
        for x, s, rr, ex in itertools.product(XS, SS, RRS, EXITS):
            for i, mv, mon_end, fri_end in lst:
                if abs(mv) <= x / 100:
                    continue
                side = -1 if mv > 0 else 1
                e = A["ask_open"][i] if side == 1 else A["bid_open"][i]
                stop, tgt = e * (1 - side * s / 100), e * (1 + side * rr * s / 100)
                j, px = walk(t, A["bid_open"], A["bid_high"], A["bid_low"], A["ask_open"], A["ask_high"], A["ask_low"],
                             i, side, stop, tgt, mon_end if ex == "day" else fri_end)
                if j < 0:
                    continue
                rows.append((a, x, s, rr, ex, t[i], t[j], side * (px / e - 1) * 1e4))
    df = pd.DataFrame(rows, columns=["anchor", "x", "s", "rr", "exit", "t_in", "t_out", "bp"])
    df["pair"] = pair
    return df


def his_fingerprints():
    lab = pd.to_datetime(LABELS, format="%Y.%m.%d")
    iv = [(lab[i], lab[i + 1]) for i in range(len(lab) - 1)]
    days = np.array([(b - a).days for a, b in iv])
    th = pd.read_csv("explore_fx/figures/their_curve_digitised.csv", parse_dates=["date"]).set_index("date").balance
    q = th.resample("QE").last().diff()
    q.index = q.index.to_period("Q")
    return iv, np.log(1 / days), q.dropna()


def score(group, iv, his_rate, his_q):
    tin = pd.to_datetime(group.t_in)
    tout = pd.to_datetime(group.t_out)
    broker_days = np.r_[(tin + pd.Timedelta("7h")).dt.dayofweek, (tout + pd.Timedelta("7h")).dt.dayofweek]
    wd = np.bincount(broker_days[broker_days < 5], minlength=5) + 0.5
    p = wd / wd.sum()
    loglik = float((HIS_WEEKDAYS * np.log(p)).sum())
    cnt = np.array([((tin >= a) & (tin < b)).sum() for a, b in iv])
    days = np.array([(b - a).days for a, b in iv])
    rate = np.log(cnt / days + 1e-3)
    timing = np.corrcoef(rate, his_rate)[0, 1] if rate.std() > 0 else 0.0
    q = group.bp.groupby(tout.dt.to_period("Q")).sum()
    j = pd.concat([his_q, q], axis=1).dropna()
    pnl = np.corrcoef(j.iloc[:, 0], j.iloc[:, 1])[0, 1] if len(j) > 4 and j.iloc[:, 1].std() > 0 else 0.0
    together = tin.value_counts()
    paired = float((together[together >= 2].sum()) / len(tin))
    weekly = group.bp.groupby(tout.dt.to_period("W")).sum()
    eq = weekly.cumsum()
    dd = float((eq.cummax() - eq).max())
    yrs = (END - START).days / 365.25
    return dict(trades=len(group), win=float((group.bp > 0).mean()), bp=float(group.bp.mean()),
                weekday_loglik=loglik, timing=timing, pnl_corr=pnl, paired=paired,
                ret_dd=float(eq.iloc[-1] / yrs / dd) if dd > 0 else 0.0,
                mon_share=float(wd[0] / wd.sum()))


def score_job(args):
    key, trios = args
    out = []
    for trio in trios:
        g = pd.concat([GROUPS[(key, p)] for p in trio if (key, p) in GROUPS])
        if len(g) < 30:
            continue
        r = score(g, IV, HIS_RATE, HIS_Q)
        out.append(dict(anchor=key[0], x=key[1], s=key[2], rr=key[3], exit=key[4], pairs="+".join(trio), **r))
    return out


GROUPS = {}
IV = HIS_RATE = HIS_Q = None

if __name__ == "__main__":
    import os, sys
    cached = "cache/weekend_match_trades.parquet"
    if os.path.exists(cached) and "--resim" not in sys.argv:       # reuse the simulated trades
        trades = pd.read_parquet(cached)
    else:
        with mp.get_context("fork").Pool(4) as pool:                 # 1-minute frames are large
            trades = pd.concat(pool.map(run_pair, PAIRS), ignore_index=True)
        trades = trades[(pd.to_datetime(trades.t_in) >= START) & (pd.to_datetime(trades.t_in) < END)]
        trades.to_parquet(cached)
    IV, HIS_RATE, HIS_Q = his_fingerprints()
    keys = ["anchor", "x", "s", "rr", "exit"]
    for key, g in trades.groupby(keys + ["pair"]):
        GROUPS[(tuple(key[:5]), key[5])] = g
    configs = sorted({k for k, _ in GROUPS})
    trios = list(itertools.combinations(PAIRS, 3))
    with mp.get_context("fork").Pool(14) as pool:
        res = pool.map(score_job, [(k, trios) for k in configs])
    out = pd.DataFrame([r for part in res for r in part])
    out.to_csv("explore_fx/weekend_match.csv", index=False, float_format="%.4f")
    print(f"{len(out)} candidates scored")
