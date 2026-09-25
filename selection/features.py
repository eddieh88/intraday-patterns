"""Stage B of prereg/selection.md: the 09:45 feature table.

Input is stage A's per-session rows. AT0945 columns may be used on their own
day; EOD columns only through .shift(1) or later. Every history window is on
the market calendar (a wide dates x symbols frame), so a name that misses a
day gets a gap, not a longer window.

Implementation choices not spelled out in the registration are recorded in its
Amendment 2, before any outcome was computed:
  - body ratio is dropped: it equals the signal size by construction
  - room-to-level is capped at 10R when no level lies ahead
  - minimum history: ATR14 10 sessions, ATR100 50, 20-day means 10, 60-day
    beta and correlation 40
  - sector ETF = highest correlation of daily close-to-close returns, prior 60

  python3 selection/features.py   -> cache/sel_features.parquet
"""
import pandas as pd, numpy as np, sys
sys.path.insert(0, "lib")
from holdout import assert_sealed

SECTORS = ["XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLU","XLB","XLRE","XLC","SMH"]
ROOM_CAP = 10.0

def wide(df, col):
    return df.pivot(index="date", columns="symbol", values=col).sort_index()

def long(w, name):
    return w.stack(future_stack=True).rename(name)

def build(S, E, pool, fomc):
    """S, E: stage A stock and ETF rows. pool: date, symbol, rk. fomc: decision dates."""
    dates = pd.DatetimeIndex(sorted(S.date.unique()))
    W = {c: wide(S, c).reindex(dates) for c in
         ["o930","c940","h15","l15","v15","r1","pre_hi","pre_lo","pre_dv",
          "rth_hi","rth_lo","rth_c"]}
    X = {c: wide(E, c).reindex(dates) for c in ["o930","c940","rth_c"]}

    # ---- history, all lagged at least one session -------------------------------
    rng   = W["rth_hi"] - W["rth_lo"]
    atr14 = rng.rolling(14, min_periods=10).mean().shift(1)
    atr100= rng.rolling(100, min_periods=50).mean().shift(1)
    pdc, pdh, pdl = W["rth_c"].shift(1), W["rth_hi"].shift(1), W["rth_lo"].shift(1)
    y_rng = rng.shift(1)
    nr7   = (y_rng <= y_rng.rolling(7, min_periods=7).min()).astype(float).where(y_rng.notna())
    inside= ((W["rth_hi"].shift(1) < W["rth_hi"].shift(2)) &
             (W["rth_lo"].shift(1) > W["rth_lo"].shift(2))).astype(float).where(W["rth_hi"].shift(2).notna())
    trend20 = W["rth_c"].shift(1) / W["rth_c"].shift(21) - 1
    pre_dv20 = W["pre_dv"].rolling(20, min_periods=10).mean().shift(1)
    v15_20   = W["v15"].rolling(20, min_periods=10).mean().shift(1)
    ret   = W["rth_c"].pct_change(fill_method=None)            # day t uses close t: EOD
    eret  = X["rth_c"].pct_change(fill_method=None)
    spy   = eret["SPY"]
    beta  = (ret.rolling(60, min_periods=40).cov(spy)
             .div(spy.rolling(60, min_periods=40).var(), axis=0)).shift(1)
    corr  = np.stack([ret.rolling(60, min_periods=40).corr(eret[e]).shift(1).values for e in SECTORS])
    ok    = ~np.isnan(corr).all(axis=0)
    sec_i = np.where(ok, np.nanargmax(np.where(np.isnan(corr), -np.inf, corr), axis=0), -1)
    spy_rv20 = (spy.rolling(20, min_periods=15).std() * np.sqrt(252)).shift(1)

    # ---- the day itself, known by 09:45 --------------------------------------------
    o, c, h, l = W["o930"], W["c940"], W["h15"], W["l15"]
    R    = h - l
    side = np.sign(c - o)
    stock_ret = c / o - 1
    ewin = X["c940"] / X["o930"] - 1
    sec_ret = np.full(o.shape, np.nan)
    for k, e in enumerate(SECTORS):                             # each name's own sector ETF
        m = sec_i == k
        sec_ret[m] = np.broadcast_to(ewin[e].values[:, None], o.shape)[m]
    sec_ret = pd.DataFrame(sec_ret, index=dates, columns=o.columns)
    spy_win = ewin["SPY"]
    vixy = X["c940"]["VIXY"] / X["rth_c"]["VIXY"].shift(1) - 1

    # room to the next level in the trade direction, in R
    levels = np.stack([x.values for x in (pdh, pdl, W["pre_hi"], W["pre_lo"])])
    ahead = (levels - c.values) * side.values                  # > 0 only for a level in front of the trade
    ahead[~(ahead > 0)] = np.nan
    with np.errstate(all="ignore"):
        nearest = np.nanmin(np.where(np.isnan(ahead), np.inf, ahead), axis=0)   # inf = nothing ahead
        room = np.minimum(nearest / R.values, ROOM_CAP)
    room[np.isnan(R.values) | np.isnan(c.values) | np.isnan(levels).all(axis=0)] = np.nan
    room_R = pd.DataFrame(room, index=dates, columns=o.columns)

    F = {
        "side": side,
        "R_bp": R / o * 1e4,
        "gap": (o - pdc) / atr14,
        "pre_dv_rel": W["pre_dv"] / pre_dv20,
        "pre_range": (W["pre_hi"] - W["pre_lo"]) / atr14,
        "or15_range": R / atr14,
        "or15_relvol": W["v15"] / v15_20,
        "first_bar_share": W["r1"] / R,
        "signal_size": (c - o).abs() / R,
        "spy_aligned": side.mul(spy_win, axis=0),
        "sector_aligned": side * sec_ret,
        "resid_aligned": side * (stock_ret - beta.mul(spy_win, axis=0)),
        "vixy_ret": pd.DataFrame(np.repeat(vixy.values[:, None], len(o.columns), 1), index=dates, columns=o.columns),
        "atr_ratio": atr14 / atr100,
        "spy_rv20": pd.DataFrame(np.repeat(spy_rv20.values[:, None], len(o.columns), 1), index=dates, columns=o.columns),
        "trend20_aligned": side * trend20,
        "dist_pdh": (c - pdh) / atr14,
        "dist_pdl": (c - pdl) / atr14,
        "room_R": room_R,
        "nr7": nr7, "inside_day": inside,
        "log_price": np.log(o),
    }
    T = pd.concat([long(v, k) for k, v in F.items()], axis=1).reset_index()
    T = T.rename(columns={"level_0": "date"}) if "level_0" in T else T

    # ---- restrict to the universe, then session-level features ------------------------
    P = pool[["date","symbol","rk"]].rename(columns={"rk": "pool_rank"})
    T = T.merge(P, on=["date","symbol"], how="inner")
    T = T[T.side.notna() & (T.side != 0)]
    br = T.assign(up=(T.side > 0).astype(float)).groupby("date").up.mean().rename("breadth")
    T = T.merge(br, on="date")

    # ---- calendar -----------------------------------------------------------------------
    sess = pd.Series(dates)
    fset = set(pd.to_datetime(fomc))
    prev = dict(zip(sess.iloc[1:], sess.iloc[:-1]))
    last_of_month = set(sess.groupby([sess.dt.year, sess.dt.month]).max())
    opex = set()
    for (y, m), g in sess.groupby([sess.dt.year, sess.dt.month]):
        fridays = pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D")
        third = fridays[(fridays.month == m) & (fridays.dayofweek == 4)][2]
        opex.add(g[g <= third].max())                           # the third Friday, or the session before
    T["dow"] = T.date.dt.dayofweek
    T["month_end"] = T.date.isin(last_of_month).astype(int)
    T["opex"] = T.date.isin(opex).astype(int)
    T["fomc_day"] = T.date.isin(fset).astype(int)
    T["fomc_next"] = T.date.map(lambda d: prev.get(d) in fset).astype(int)
    return T.sort_values(["date","symbol"]).reset_index(drop=True)

def main():
    S = pd.read_parquet("cache/sel_stocks.parquet"); E = pd.read_parquet("cache/sel_etfs.parquet")
    pool = pd.read_parquet("cache/intraday_pool.parquet"); pool = pool[pool.rk <= 100]
    fomc = pd.read_csv("data/calendar/fomc_decisions.csv", parse_dates=["date"]).date
    T = build(S, E, pool, fomc)
    assert_sealed(T.date)
    T.to_parquet("cache/sel_features.parquet", index=False)
    feats = [c for c in T.columns if c not in ("date","symbol","side","R_bp")]
    print(f"{len(T):,} name-days, {T.date.nunique()} sessions, {T.date.min().date()} -> {T.date.max().date()}")
    print(f"complete rows (every feature present): {T[feats].notna().all(axis=1).mean():.1%}")
    print(T[feats].describe(percentiles=[.05,.5,.95]).T[["count","mean","5%","50%","95%"]].round(3).to_string())

if __name__ == "__main__":
    main()
