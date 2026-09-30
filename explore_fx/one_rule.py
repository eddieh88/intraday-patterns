"""EXPLORATORY. Which one-rule, one-parameter mean-reversion families could produce the
equity curve in an X post ("one timeframe, same parameters/management, one specific
parameter, multi-asset FX")? Currency futures, development period only (2021-01 to
2025-03). His curve runs from 2018 on spot FX, so this can only check resemblance.

His curve, read off the MT5 chart: about +1.4% a year, max drawdown about 1.6%. The
x-axis counts trades, and trades bunch in 2022 and 2025-26, the volatile years.

Families (both sides, entry and exit at the next bar's open, no stop):
  bb    close beyond SMA(N) +/- 2 sd       -> exit at a close back across SMA(N)
  rsi   RSI(N) < 30 / > 70                 -> exit when RSI crosses 50
  nbar  close is the lowest/highest of N   -> exit at the first close against it
  ibs   (close-low)/(high-low) < p / > 1-p -> exit after one bar
  big   a bar with range > k x ATR(20), faded against its close -> exit after one bar
  pct   a close-to-close move > x% (FIXED, not volatility-scaled), faded -> exit after one bar
  dist  close more than x% (FIXED) from SMA(20), faded   -> exit at a close back across SMA(20)
Cost: 1.5 ticks round trip (spread + commission). Returns are in ATR(20) units, so
every market carries the same risk.

  python3 explore_fx/one_rule.py  -> explore_fx/one_rule_dev.csv
"""
import glob
import multiprocessing as mp
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from holdout import HOLDOUT_START

TICK = {"E6": 0.00005, "J1": 0.0000005, "B6": 0.0001, "A6": 0.00005, "N6": 0.00005, "E1": 0.00005}
TF = {"H1": dict(rule="1h"), "H4": dict(rule="4h", offset="1h"), "D1": dict(rule="1D", offset="17h")}
GRID = {"bb": [10, 20, 50], "rsi": [2, 5, 14], "nbar": [5, 10, 20], "ibs": [0.1, 0.2], "big": [1.5, 2.0, 3.0],
        "pct": [0.25, 0.5, 1.0], "dist": [0.5, 1.0, 2.0]}


def load(period="dev"):
    """dev: before 2025-04-01. holdout: from 2025-04-01, sealed unless HOLDOUT_UNLOCK=final-evaluation"""
    rows = []
    for f in sorted(glob.glob("cache/mp_futures_5min/*.parquet")):
        if (pd.Timestamp(f.split("_")[-1][:10]) >= HOLDOUT_START) != (period == "holdout"):
            continue
        rows.append(pq.read_table(f, filters=[("symbol", "in", list(TICK))]).to_pandas())
    d = pd.concat(rows)
    d["ts"] = pd.to_datetime(d.timestamp)
    if period == "holdout":
        assert_sealed(d.ts)
    return {s: g.drop_duplicates("ts").set_index("ts").sort_index()[["open", "high", "low", "close"]]
            for s, g in d.groupby("symbol")}


def bars(m, tf):
    return m.resample(label="left", closed="left", **TF[tf]).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def signals(b, fam, p):
    """-> (side wanted at this close: +1/-1/0 entry, exit condition per side as arrays)"""
    c, h, l = b.close, b.high, b.low
    if fam == "bb":
        m, s = c.rolling(p).mean(), c.rolling(p).std()
        return np.sign((c < m - 2 * s).astype(int) - (c > m + 2 * s).astype(int)), (c >= m), (c <= m), None
    if fam == "rsi":
        r = rsi(c, p)
        return np.sign((r < 30).astype(int) - (r > 70).astype(int)), (r >= 50), (r <= 50), None
    if fam == "nbar":
        lo, hi = c == c.rolling(p).min(), c == c.rolling(p).max()
        return np.sign(lo.astype(int) - hi.astype(int)), (c > c.shift()), (c < c.shift()), None
    if fam == "ibs":
        ibs = (c - l) / (h - l)
        return np.sign((ibs < p).astype(int) - (ibs > 1 - p).astype(int)), None, None, 1
    if fam == "pct":
        r = c / c.shift() - 1
        return -np.sign(r) * (r.abs() > p / 100), None, None, 1
    if fam == "dist":
        m = c.rolling(20).mean()
        d = c / m - 1
        return -np.sign(d) * (d.abs() > p / 100), (c >= m), (c <= m), None
    if fam == "big":
        pc = c.shift()
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        a = tr.rolling(20).mean().shift()
        big = (h - l) > p * a
        return -np.sign(c - b.open) * big, None, None, 1


def backtest(b, fam, p, tick):
    ent, ex_long, ex_short, hold = signals(b, fam, p)
    ent = np.nan_to_num(np.asarray(ent, float))
    xl = None if ex_long is None else np.asarray(ex_long)
    xs = None if ex_short is None else np.asarray(ex_short)
    pc = b.close.shift()
    tr = pd.concat([b.high - b.low, (b.high - pc).abs(), (b.low - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean().values
    O, ts = b.open.values, b.index
    trades, pos = [], 0
    for i in range(20, len(b) - 1):
        if pos:
            done = (i - k >= hold) if hold else (xl[i] if pos == 1 else xs[i])
            if done:
                trades.append((ts[k + 1], ts[i + 1], pos, (pos * (O[i + 1] - O[k + 1]) - 1.5 * tick) / atr[k]))
                pos = 0
        if not pos and ent[i] != 0 and atr[i] > 0:
            pos, k = int(ent[i]), i
    return pd.DataFrame(trades, columns=["t_in", "t_out", "side", "r"])


def run(job):
    tf, fam, p = job
    out = []
    for s, m in DATA.items():
        t = backtest(bars(m, tf), fam, p, TICK[s])
        out.append(t.assign(sym=s))
    t = pd.concat(out)
    daily = t.groupby(t.t_out.dt.normalize()).r.sum()
    daily = daily.reindex(pd.date_range("2021-01-04", "2025-03-31", freq="B"), fill_value=0)
    eq = daily.cumsum()
    yrs = 4.24
    per_year = t.t_in.dt.year.value_counts()
    return dict(tf=tf, family=fam, param=p, trades=len(t), trades_per_yr=len(t) / yrs,
                win=(t.r > 0).mean(), mean_r=t.r.mean(), t_stat=t.r.mean() / t.r.std() * np.sqrt(len(t)),
                sharpe=daily.mean() / daily.std() * np.sqrt(252),
                ret_over_dd=eq.iloc[-1] / (eq.cummax() - eq).max(),
                hold_days=((t.t_out - t.t_in).dt.total_seconds() / 86400).median(),
                n2022_vs_2021=per_year.get(2022, 0) / max(per_year.get(2021, 1), 1),
                pct_years_up=(t.groupby(t.t_out.dt.year).r.sum() > 0).mean())


DATA = {}
if __name__ == "__main__":
    DATA.update(load())
    jobs = [(tf, fam, p) for tf in TF for fam, ps in GRID.items() for p in ps]
    with mp.get_context("fork").Pool(12) as pool:
        rows = pool.map(run, jobs)
    out = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    out.to_csv("explore_fx/one_rule_dev.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))
