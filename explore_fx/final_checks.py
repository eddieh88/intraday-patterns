"""EXPLORATORY, development only (2015-01 .. 2026-09). The expert's last round, after the sealed
2010-2014 test of the evening basket fade failed net and passed gross (prereg/own_fx_basket.md).
2010-2014 is spent for this family, so nothing here can be confirmed on sealed data.

A. Cost-reduced basket: EUR+GBP+AUD (and the original EUR+AUD+NZD for comparison), the same
   36-variant region (prev_close, 0.4%), no entries 17:00-17:20 New York, simulated at the mid
   and charged ECN round trips per leg: EURUSD 0.55, GBPUSD 0.8, AUDUSD 1.0, NZDUSD 1.6 pips.
   Bar: >= +100 bp/yr net.
B. Trend filter (fixed before looking): skip fades against the sign of the dollar basket's
   12-month return (computed from daily closes up to the day before).
C. His trigger, two candidates (HistData bid/ask, stop 30 pips, no target, exit 17:15 New York,
   one trade per pair per day), scored on his fingerprints:
   env50 / env100 : H1 close beyond SMA(50 / 100) +- X%, X in {0.2, 0.3, 0.4, 0.6}, checked at
                    H1 closes 01:00-09:00 New York -> fade
   asia_range     : the 00:00-07:00 London range; at H1 closes 07:00-12:00 London, a close beyond
                    the range by >= X pips (X in {5, 10, 20, 30}) -> fade
"""
import itertools
import multiprocessing as mp
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import data
import basket_match as B
from weekend_match import walk, his_fingerprints, score

S0, S1 = pd.Timestamp("2015-01-05"), pd.Timestamp("2026-09-25")
ECN = {"eurusd": 0.55, "gbpusd": 0.8, "audusd": 1.0, "nzdusd": 1.6, "usdjpy": 0.7}
PX = {"eurusd": 1.12, "gbpusd": 1.30, "audusd": 0.70, "nzdusd": 0.64, "usdjpy": 125.0}


# ---------- A + B: the basket region at ECN costs, with and without the trend filter ----------
def basket_trades(trio):
    fr = {}
    for p in trio:
        d = data.load(p, "dev")
        d = d[(d.index >= S0 - pd.Timedelta("10D")) & (d.index < S1)]
        sp = d.spread_mean
        ok = (sp <= 3 * sp.median()) & (sp <= sp.shift(1).rolling(4, min_periods=1).mean().fillna(np.inf) + 1e-9)
        ok &= ~((d.index.hour == 17) & (d.index.minute < 20))           # skip the 17:00-17:20 spread spike
        d = d.assign(ok=ok)
        for s in ("bid", "ask"):
            for c in ("open", "high", "low", "close"):
                d[f"{s}_{c}"] = d[f"mid_{c}"]
        fr[p] = d
    idx = fr[trio[0]].index
    for p in trio[1:]:
        idx = idx.intersection(fr[p].index)
    B.FR.clear(); B.FR.update({p: fr[p].reindex(idx) for p in trio}); B.IDX = idx
    B.START, B.END = S0, S1
    B.XS, B.WS, B.SS, B.CS = (0.4,), (6, 8, 10), (25, 30, 40, None), ("lon17", "ny11", "ny1655")
    t = B.run(trio)
    t = t[t.ref == "prev_close"].copy()
    t["bp"] = t.bp - t.pair.map(ECN) * t.pair.map(B.PIP) / t.pair.map(PX) * 1e4
    # dollar 12-month trend at entry: + = USD up over the year before the entry day
    daily = pd.DataFrame({p: fr[p].mid_close.resample("1D").last() for p in trio}).dropna()
    usd = (np.log(daily) * np.array([B.USD_SIGN[p] for p in trio])).mean(axis=1)
    trend = np.sign(usd - usd.shift(252)).shift(1)
    t["t_in"], t["t_out"] = pd.to_datetime(t.t_in), pd.to_datetime(t.t_out)
    t["trend"] = trend.reindex(t.t_in.dt.normalize()).values
    return t


def region_curve(t, filt):
    """Equal-weight daily P&L of the 36 variants. filt: keep only fades in the direction of the
    dollar's 12-month trend (usd_side = +1 buys USD)."""
    days = pd.bdate_range(S0, S1 - pd.Timedelta("1D"))
    t = t.assign(usd_side=t.side * t.pair.map(B.USD_SIGN))
    if filt:
        t = t[t.usd_side == t.trend]
    curves = []
    for _, g in t.groupby(["W", "close", "stop"]):
        per = g.groupby("t_in").agg(bp=("bp", "sum"), t_out=("t_out", "max"))
        per["bp"] /= 3
        curves.append(per.groupby(per.t_out.dt.normalize()).bp.sum().reindex(days, fill_value=0.0))
    while len(curves) < 36:                                  # variants with no trades left count as flat
        curves.append(pd.Series(0.0, index=days))
    return pd.concat(curves, axis=1).mean(axis=1)


def summarize(label, daily):
    yr = daily.groupby(daily.index.year).sum()
    eq = daily.cumsum()
    dd = (eq.cummax() - eq).max()
    mean = eq.iloc[-1] / (len(daily) / 252)
    print(f"{label:<44} mean {mean:+5.0f} bp/yr  years+ {(yr > 0).sum()}/{len(yr)}  ret/maxDD {mean / dd if dd else 0:.2f}  "
          f"by year {yr.round(0).astype(int).to_dict()}")


# ---------- C: per-pair trigger candidates at the hourly close ----------
PAIRS = ["eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]


def trigger_trades(pair):
    d = data.load(pair, "dev")
    d = d[(d.index >= S0 - pd.Timedelta("10D")) & (d.index < S1)]
    t = d.index.values.astype("int64")
    bo, bh, bl, ao, ah, al = (d[c].values for c in ("bid_open", "bid_high", "bid_low", "ask_open", "ask_high", "ask_low"))
    pip = B.PIP[pair]
    h = d.mid_close.resample("1h", label="right", closed="right").last().dropna()
    lon = h.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("Europe/London")
    lon_h = np.asarray(lon.hour, float)
    lon_day = pd.Series(lon.tz_localize(None).normalize(), index=h.index)
    feats = {}
    for n in (50, 100):
        feats[f"env{n}"] = ((h / h.rolling(n).mean() - 1) * 100).values
    hr = h.index.hour
    rows = []
    ok_day = (h.index >= S0) & (h.index.dayofweek < 5) & ~(((h.index.month == 12) & (h.index.day >= 17)) | ((h.index.month == 1) & (h.index.day <= 5)))

    def trade(k, side, cond, X):
        i = d.index.searchsorted(h.index[k])
        if i >= len(t):
            return
        e = ao[i] if side == 1 else bo[i]
        t_exit = (h.index[k].normalize() + pd.Timedelta("17:15:00")).value
        j, px = walk(t, bo, bh, bl, ao, ah, al, i, side, e - side * 30 * pip, e + side * 1e6 * pip, t_exit)
        if j >= 0:
            rows.append((cond, X, t[i], t[j], side * (px - e) / pip, side * (px / e - 1) * 1e4, h.index[k].value))

    for cond in ("env50", "env100"):
        f = feats[cond]
        for X in (0.2, 0.3, 0.4, 0.6):
            seen = set()
            for k in np.flatnonzero(ok_day & (hr >= 1) & (hr <= 9) & (np.abs(f) >= X)):
                day = h.index[k].normalize()
                if day not in seen:
                    seen.add(day)
                    trade(k, -1 if f[k] > 0 else 1, cond, X)
    # Asian range: 00:00-07:00 London of the same London day
    in_range = (lon_h >= 0) & (lon_h < 7)
    rng = pd.DataFrame({"h": h.values, "day": lon_day.values, "r": in_range})
    hi = rng[rng.r].groupby("day").h.max()
    lo = rng[rng.r].groupby("day").h.min()
    rh, rl = lon_day.map(hi).values, lon_day.map(lo).values
    for X in (5, 10, 20, 30):
        seen = set()
        win = ok_day & (lon_h >= 7) & (lon_h <= 12)
        for k in np.flatnonzero(win & ((h.values > rh + X * pip) | (h.values < rl - X * pip))):
            day = lon_day.iloc[k]
            if day not in seen:
                seen.add(day)
                trade(k, -1 if h.values[k] > rh[k] else 1, "asia_range", X)
    df = pd.DataFrame(rows, columns=["cond", "X", "t_in", "t_out", "pips", "bp", "bar"])
    df["pair"] = pair
    return df


if __name__ == "__main__":
    print("=== A/B: basket region at ECN costs (mid + per-leg cost), 2015-2026 ===")
    for trio in (("eurusd", "audusd", "nzdusd"), ("eurusd", "gbpusd", "audusd")):
        t = basket_trades(trio)
        summarize("+".join(trio) + " ECN", region_curve(t, False))
        summarize("+".join(trio) + " ECN + 12m trend filter", region_curve(t, True))
    print("\n=== C: his-trigger candidates (HistData bid/ask, stop 30, exit 17:15 NY) ===")
    with mp.get_context("fork").Pool(5) as pool:
        tt = pd.concat(pool.map(trigger_trades, PAIRS), ignore_index=True)
    iv, his_rate, his_q = his_fingerprints()
    out = []
    for key, g0 in tt.groupby(["cond", "X"]):
        for trio in itertools.combinations(PAIRS, 3):
            g = g0[g0.pair.isin(trio)]
            if len(g) < 30:
                continue
            g = g[(pd.to_datetime(g.t_in) >= pd.Timestamp("2018-01-01")) & (pd.to_datetime(g.t_in) < pd.Timestamp("2026-08-01"))]
            if len(g) < 30:
                continue
            r = score(g, iv, his_rate, his_q)
            sizes = g.groupby("bar").size()
            yc = pd.to_datetime(g.t_in).dt.year.value_counts()
            out.append(dict(cond=key[0], X=key[1], trio="+".join(trio), **r,
                            per_pair_month=len(g) / 3 / 8.6 / 12, scratch=float((g.pips.abs() <= 8).mean()),
                            grp2plus=float((sizes >= 2).mean()),
                            ratio_2022_2021=float(yc.get(2022, 0) / max(yc.get(2021, 1), 1))))
    res = pd.DataFrame(out)
    res.to_csv("explore_fx/final_checks_triggers.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 260)
    cols = ["ret_dd", "win", "scratch", "mon_share", "weekday_loglik", "timing", "pnl_corr", "per_pair_month", "grp2plus", "ratio_2022_2021"]
    print(res.groupby(["cond", "X"])[cols].median().round(2).to_string())
