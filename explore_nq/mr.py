"""A long-only intraday mean-reversion system on NQ, as posted by @MrMilkTrading,
plus the scale-in variant suggested in a reply. Rules (prereg/nq_mean_reversion.md):

  bars     : NQ 3-minute candles, signals from candles closing 10:03-11:57 New York
             (9:00-11:00 CT). Long only, one order or position at a time.
  filter   : efficiency ratio of the last 15 closes <= 0.35
  entry    : at the candle's close, a buy limit at close - 1.0 x ATR(14); filled only
             if price trades 1 tick through it; cancelled after 9 minutes
  target   : the middle of the signal candle (a limit, no slippage)
  stop     : 1.5 x ATR below the (first) limit
  time     : exit 15 minutes after the fill; flat at 12:00 New York
  costs    : 1 tick slippage on stops and market exits (his rule 7), plus a
             commission reported separately

He fills on 1-second data. We have 1-minute bars, so the order of events inside a
minute is unknown. The primary run takes the losing order everywhere, as his rule 7
does: adds before the stop, the stop before the target, and no target in the minute
of the fill. `optimistic=True` credits a target in the fill minute, to bracket it.

  python3 explore_nq/mr.py            -> development (to 2025-03-31)
  python3 explore_nq/mr.py holdout    -> holdout (sealed unless HOLDOUT_UNLOCK=final-evaluation)
"""
import glob, os, sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from holdout import HOLDOUT_START, assert_sealed

TICK = 0.25
COMMISSION = 0.225              # points per contract round trip (~$4.50 on NQ)
WINDOW = ("10:00:00", "12:00:00")     # New York time = 9:00-11:00 CT


def load_nq(period="dev"):
    """1-minute NQ bars (New York time, labelled at the bar's start), cached."""
    out = f"cache/nq_1min_{period}.parquet"
    if not os.path.exists(out):
        rows = []
        for f in sorted(glob.glob("cache/mp_futures_1min/*.parquet")):
            if (pd.Timestamp(f.split("_")[-1][:10]) >= HOLDOUT_START) != (period == "holdout"):
                continue
            rows.append(pq.read_table(f, filters=[("symbol", "=", "NQ")]).to_pandas())
        d = pd.concat(rows)
        d["ts"] = pd.to_datetime(d.timestamp)
        if period == "holdout":
            assert_sealed(d.ts)
        d = d.drop_duplicates("ts").sort_values("ts").set_index("ts")[["open", "high", "low", "close"]]
        d.to_parquet(out)
    d = pd.read_parquet(out)
    if period == "holdout":
        assert_sealed(d.index)
    return d


def bars3(m1):
    """3-minute candles on the clock grid (10:00, 10:03, ...), labelled at the start."""
    b = m1.resample("3min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    return b


def efficiency_ratio(close, n=15):
    """|net change over n closes| / sum of |close-to-close changes| over the same n."""
    net = close.diff(n).abs()
    path = close.diff().abs().rolling(n).sum()
    return net / path


def atr(b, n=14):
    """Wilder's ATR, as in NinjaTrader."""
    pc = b.close.shift()
    tr = pd.concat([b.high - b.low, (b.high - pc).abs(), (b.low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def simulate(m1, b3, levels=((1.0, 1.0),), er_max=0.35, stop_atr=1.5, cancel_min=9,
             time_stop=15, optimistic=False):
    """levels: (ATR multiple below the close, fraction of the position) for each limit.
    The first level is the signal's; the others are scale-in adds, live until the
    position exits. b3 may carry precomputed `er` and `atr` columns.
    -> one row per filled trade."""
    if "er" not in b3:
        b3 = b3.assign(er=efficiency_ratio(b3.close), atr=atr(b3))
    trades = []
    for day, sig in b3.groupby(b3.index.normalize()):
        t0, t1 = day + pd.Timedelta(WINDOW[0]), day + pd.Timedelta(WINDOW[1])
        sig = sig[(sig.index >= t0) & (sig.index + pd.Timedelta("3min") < t1)]
        mm = m1[(m1.index >= t0) & (m1.index < t1 + pd.Timedelta("1min"))]
        if sig.empty or mm.empty:
            continue
        ts, O, H, L, C = mm.index, mm.open.values, mm.high.values, mm.low.values, mm.close.values
        free_at = t0
        for s, r in sig.iterrows():
            close_t = s + pd.Timedelta("3min")
            if close_t < free_at or not (r.er <= er_max):
                continue
            px = [r.close - k * r.atr for k, _ in levels]
            w = [f for _, f in levels]
            cancel = min(close_t + pd.Timedelta(minutes=cancel_min), t1)
            i = ts.searchsorted(close_t)
            j_end = ts.searchsorted(cancel)
            f = next((j for j in range(i, j_end) if L[j] <= px[0] - TICK), None)
            if f is None:
                free_at = cancel
                continue
            target = (r.high + r.low) / 2
            stop = px[0] - stop_atr * r.atr
            t_exit = min(ts[f] + pd.Timedelta(minutes=time_stop), t1)
            filled = [False] * len(px)
            exit_px = why = None
            j = f
            while j < len(ts):
                if ts[j] >= t_exit:                     # time stop or 12:00, at the open
                    exit_px, why = O[j] - TICK, "time" if t_exit < t1 else "12:00"
                    break
                for q in range(len(px)):                # adds first: the losing order
                    if not filled[q] and L[j] <= px[q] - TICK:
                        filled[q] = True
                if L[j] <= stop:
                    exit_px, why = stop - TICK, "stop"
                    break
                if H[j] >= target + TICK and (j > f or optimistic):
                    exit_px, why = target, "target"
                    break
                j += 1
            if exit_px is None:                         # data ends before 12:00
                j = len(ts) - 1
                exit_px, why = C[j] - TICK, "data"
            wf = np.array(w) * np.array(filled)
            pts = float(sum(wf[q] * (exit_px - px[q]) for q in range(len(px))))
            trades.append(dict(
                day=day, signal=s, fill_t=ts[f], exit_t=ts[j], why=why, entry=px[0],
                exit=exit_px, target=target, stop=stop, atr=r.atr, er=r.er,
                size=wf.sum(), n_fills=int(sum(filled)), pts=pts,
                pts_net=pts - COMMISSION * wf.sum()))
            free_at = ts[j] if why in ("time", "12:00") else ts[j] + pd.Timedelta("1min")
    return pd.DataFrame(trades)


def random_control(m1, trades, n=20, seed=7, time_stop=15):
    """For each trade, n market buys at random minutes of the same day's window, with
    the trade's own target and stop distances and the same exits. Separates the
    dip-limit entry from long exposure in the same hours."""
    rng = np.random.default_rng(seed)
    out = []
    for t in trades.itertuples():
        t0, t1 = t.day + pd.Timedelta(WINDOW[0]), t.day + pd.Timedelta(WINDOW[1])
        mm = m1[(m1.index >= t0) & (m1.index < t1 + pd.Timedelta("1min"))]
        ts, O, H, L, C = mm.index, mm.open.values, mm.high.values, mm.low.values, mm.close.values
        cand = np.flatnonzero(ts < t1 - pd.Timedelta("1min"))
        up, dn = t.target - t.entry, t.entry - t.stop
        res = []
        for e in rng.choice(cand, n):
            entry = O[e] + TICK
            tgt, stp = entry + up, entry - dn
            t_exit = min(ts[e] + pd.Timedelta(minutes=time_stop), t1)
            px = None
            for j in range(e, len(ts)):
                if ts[j] >= t_exit:
                    px = O[j] - TICK; break
                if L[j] <= stp:
                    px = stp - TICK; break
                if H[j] >= tgt + TICK and j > e:
                    px = tgt; break
            if px is None:
                px = C[-1] - TICK
            res.append(px - entry - COMMISSION)
        out.append(np.mean(res))
    return np.array(out)


def clustered(x, groups):
    """Mean, and its standard error clustered by group."""
    x = np.asarray(x, float)
    g = pd.Series(x).groupby(np.asarray(groups))
    m = x.mean()
    s = g.sum() - m * g.size()
    k = len(s)
    se = np.sqrt(k / (k - 1) * (s ** 2).sum()) / len(x)
    return m, se


def summary(tr, label):
    wk = tr.day.dt.to_period("W").astype(str)
    m, se = clustered(tr.pts_net, wk)
    mg, _ = clustered(tr.pts, wk)
    print(f"{label:<34} n={len(tr):>5}  win={np.mean(tr.pts > 0):5.1%}  "
          f"gross={mg:+6.2f}  net={m:+6.2f} ± {se:4.2f} pts (t {m / se:+5.2f})  "
          f"$/day={tr.pts_net.sum() * 20 / tr.day.nunique():+7.1f}")
    return m, se


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "dev"
    m1 = load_nq(period)
    b3 = bars3(m1)
    print(f"{period}: {m1.index.min().date()} to {m1.index.max().date()}, "
          f"{m1.index.normalize().nunique()} days")
    base = simulate(m1, b3)
    scale = simulate(m1, b3, levels=((1.0, 0.5), (1.5, 0.5)))
    base.to_parquet(f"cache/nq_mr_base_{period}.parquet")
    scale.to_parquet(f"cache/nq_mr_scale_{period}.parquet")
    summary(base, "A. as posted")
    summary(scale, "B. scale-in 1.0 / 1.5 ATR")
    ctrl = random_control(m1, base)
    wk = base.day.dt.to_period("W").astype(str)
    m, se = clustered(base.pts_net.values - ctrl, wk)
    print(f"{'A minus random entries':<34} control net={ctrl.mean():+6.2f}  "
          f"diff={m:+6.2f} ± {se:4.2f} pts (t {m / se:+5.2f})")
    print(base.why.value_counts().to_string())
