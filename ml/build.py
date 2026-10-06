"""Feature table for the opening-hour ML study (prereg/opening_ml.md, with Amendment 1).

One row per name-day in the day's point-in-time top 100: raw features known by
10:00, and the 10:00-11:00 target. Ranking within each day happens in the model step.

  python3 ml/build.py              -> cache/ml_open_dev.parquet
  HOLDOUT_UNLOCK=final-evaluation python3 ml/build.py holdout   (once, see the prereg)

Only three functions touch intraday bars, and each slices before its cutoff:
  opening()     stock bars stamped before 10:00 (and pre-market)
  etf_opening() ETF bars stamped before 10:00
  macro_at()    futures bars stamped at or before 09:58
tests/test_ml_build.py changes every later bar and checks that nothing moves.
"""
import glob, sys, time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("selection")
from session_summary import session_close
from holdout import HOLDOUT_START, assert_sealed

COLS = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC", "SMH"]
ETFS = SECTORS + ["SPY"]
MACRO = ["ES", "NQ", "RTY", "ZN", "US", "ZF", "DX", "J1", "CL", "GC", "VX", "BTC"]
BETA_ON = ["ES", "ZN", "DX", "CL", "VX"]
HIST, BETA_N, BETA_MIN = 65, 60, 40
T_OPEN, T_CUT, T_MACRO = 9.5, 10.0, 9 + 58 / 60
DAY = lambda f: pd.Timestamp(f.split("_")[-1][:10])


# ---------- the only functions that read intraday bars ----------

def opening(o, h, l, c, v, hh):
    """Opening and pre-market quantities from bars stamped before 10:00."""
    pre = hh < T_OPEN
    w = (hh >= T_OPEN) & (hh < T_CUT)
    if w.sum() < 4 or not np.isclose(hh[w][0], T_OPEN):
        return None
    i = np.flatnonzero(w)
    tp = (h[i] + l[i] + c[i]) / 3
    i940 = i[hh[i] < 9.75]
    return dict(
        o930=o[i[0]], c955=c[i[-1]], c940=c[i940[-1]] if len(i940) else np.nan,
        hi_or=h[i].max(), lo_or=l[i].min(), vol_or=v[i].sum(),
        vwap_or=(tp * v[i]).sum() / v[i].sum() if v[i].sum() > 0 else np.nan,
        pre_close=c[pre][-1] if pre.any() else np.nan,
        pre_dv=(c[pre] * v[pre]).sum() if pre.any() else 0.0)


def etf_opening(o, c, hh):
    """09:30 open to the 09:55 close, from ETF bars stamped before 10:00."""
    w = (hh >= T_OPEN) & (hh < T_CUT)
    if not w.any() or not np.isclose(hh[w][0], T_OPEN):
        return np.nan
    return c[w][-1] / o[w][0] - 1


def macro_at(ts_h, close, t):
    """The last close at or before hour t (bars stamped <= t)."""
    k = np.flatnonzero(ts_h <= t + 1e-9)
    return close[k[-1]] if len(k) else np.nan


# ---------- end-of-day records, used only on later days ----------

def eod(o, h, l, c, v, hh, close_h):
    rth = (hh >= T_OPEN) & (hh < close_h)
    if rth.sum() < 10:
        return None
    i = np.flatnonzero(rth)
    a, b = np.flatnonzero(rth & np.isclose(hh, 10.0)), np.flatnonzero(rth & np.isclose(hh, 10 + 55 / 60))
    lh = np.flatnonzero(rth & (hh >= close_h - 1))
    return dict(open=o[i[0]], close=c[i[-1]], hi=h[i].max(), lo=l[i].min(),
                r1011=c[b[0]] / o[a[0]] - 1 if len(a) and len(b) else np.nan,
                r_last=c[i[-1]] / o[lh[0]] - 1 if len(lh) else np.nan,
                dv=(c[i] * v[i]).sum())


def target(o, c, hh):
    a, b = np.flatnonzero(np.isclose(hh, 10.0)), np.flatnonzero(np.isclose(hh, 10 + 55 / 60))
    return c[b[0]] / o[a[0]] - 1 if len(a) and len(b) else np.nan


# ---------- features: opening quantities + prior days + context ----------

def lret(a, b):
    return np.log(a / b) if a > 0 and b > 0 else np.nan


def stock_row(op, H, ctx):
    """Raw features for one name-day. H: this stock's prior-session records, oldest
    first (each with date, open, close, hi, lo, r1011, r_last, dv, vol_or, pre_dv)."""
    if len(H) < 21:
        return None
    hi = np.array([x["hi"] for x in H]); lo = np.array([x["lo"] for x in H])
    cl = np.array([x["close"] for x in H]); rng = hi - lo
    atr20, atr5 = rng[-20:].mean(), rng[-5:].mean()
    y = H[-1]; c955, o930 = op["c955"], op["o930"]
    mean20 = lambda k: np.nanmean([x[k] for x in H[-20:]])
    r = dict(
        r_or=c955 / o930 - 1, r_or1=op["c940"] / o930 - 1, r_or2=c955 / op["c940"] - 1,
        or_rng_atr=(op["hi_or"] - op["lo_or"]) / atr20,
        or_vol_rel=op["vol_or"] / mean20("vol_or") if mean20("vol_or") > 0 else np.nan,
        or_pos=(c955 - op["lo_or"]) / (op["hi_or"] - op["lo_or"]) if op["hi_or"] > op["lo_or"] else 0.5,
        vwap_dev=c955 / op["vwap_or"] - 1,
        gap=o930 / y["close"] - 1, pre_ret=op["pre_close"] / y["close"] - 1,
        pre_dv_rel=op["pre_dv"] / mean20("pre_dv") if mean20("pre_dv") > 0 else np.nan,
        tod1=y["r1011"], tod5=np.nanmean([x["r1011"] for x in H[-5:]]), tod20=np.nanmean([x["r1011"] for x in H[-20:]]),
        r_prev=y["close"] / H[-2]["close"] - 1, r_prev_oc=y["close"] / y["open"] - 1, r_prev_last=y["r_last"],
        r5=y["close"] / cl[-6] - 1, r20=y["close"] / cl[-21] - 1,
        d_pdh=(c955 - y["hi"]) / atr20, d_pdl=(c955 - y["lo"]) / atr20,
        open_pos=(o930 - y["lo"]) / (y["hi"] - y["lo"]) if y["hi"] > y["lo"] else 0.5,
        atr_ratio=atr5 / atr20, atr_pct=atr20 / c955,
        log_price=np.log(c955), log_dv20=np.log(mean20("dv")) if mean20("dv") > 0 else np.nan,
        pool_rank=ctx["rank"], dow=ctx["dow"])
    # macro exposure: 60-session beta to each series, times today's move
    dates = [x["date"] for x in H[-(BETA_N + 1):]]
    sret = np.diff(np.log([x["close"] for x in H[-(BETA_N + 1):]]))
    for k in BETA_ON:
        m = np.array([ctx["macro_ret"].get(d, {}).get(k, np.nan) for d in dates[1:]])
        ok = np.isfinite(m) & np.isfinite(sret)
        if ok.sum() >= BETA_MIN and np.var(m[ok]) > 0:
            beta = np.cov(sret[ok], m[ok])[0, 1] / np.var(m[ok], ddof=1)
            r[f"mx_{k}"] = beta * ctx["macro_move"].get(k, np.nan)
        else:
            r[f"mx_{k}"] = np.nan
    # sector: the sector ETF most correlated over the prior 60 sessions
    best, bc = None, -2
    for e in SECTORS:
        m = np.array([ctx["etf_ret"].get(d, {}).get(e, np.nan) for d in dates[1:]])
        ok = np.isfinite(m) & np.isfinite(sret)
        if ok.sum() >= BETA_MIN:
            cc = np.corrcoef(sret[ok], m[ok])[0, 1]
            if cc > bc:
                best, bc = e, cc
    so = ctx["etf_or"].get(best, np.nan) if best else np.nan
    r["sec_rel_or"] = r["r_or"] - so
    r["sec_vs_spy"] = so - ctx["etf_or"].get("SPY", np.nan)
    return r


# ---------- the day loop ----------

def load(path, names):
    d = pd.read_parquet(path, columns=COLS).dropna(subset=["symbol"])
    d = d[d.symbol.isin(names)]
    t = pd.to_datetime(d.timestamp)
    return d.assign(h=(t.dt.hour + t.dt.minute / 60).values).sort_values(["symbol", "timestamp"])


def run_chunk(job):
    days, live, by_day, ranks, allnames, files = job
    H, rows = {}, []
    macro_prev, macro_ret, etf_prev, etf_ret = {}, {}, {}, {}
    for day in days:
        sf, ef, ff = files["stock"].get(day), files["etf"].get(day), files["fut"].get(day)
        if sf is None:
            continue
        full = pd.read_parquet(sf, columns=["timestamp", "volume"])
        close_h = session_close(full.assign(symbol=""))
        S = load(sf, allnames)
        E = load(ef, set(ETFS)) if ef else None
        F = load(ff, set(MACRO)) if ff else None
        # futures: today's 09:58 level, and today's close reference for tomorrow
        fut_now, fut_close = {}, {}
        if F is not None:
            for k, g in F.groupby("symbol"):
                hh, c = g.h.values, g.close.values.astype(float)
                fut_now[k] = macro_at(hh, c, T_MACRO)
                fut_close[k] = macro_at(hh, c, close_h - 1 / 60)
                if k == "ES":
                    o930 = g.open.values[np.flatnonzero(hh >= T_OPEN)[0]] if (hh >= T_OPEN).any() else np.nan
                    fut_now["ES_open"] = lret(fut_now[k], o930)
        mv = {}
        for k in MACRO:
            if k == "VX":
                mv[k] = fut_now.get(k, np.nan) - macro_prev.get(k, np.nan)
            else:
                mv[k] = lret(fut_now.get(k, np.nan), macro_prev.get(k, np.nan))
        # ETFs: opening returns today, daily closes for history
        etf_or, etf_cl = {}, {}
        if E is not None:
            for k, g in E.groupby("symbol"):
                hh = g.h.values
                etf_or[k] = etf_opening(g.open.values.astype(float), g.close.values.astype(float), hh)
                rth = (hh >= T_OPEN) & (hh < close_h)
                if rth.any():
                    etf_cl[k] = g.close.values[rth][-1]
        ctx = dict(macro_move=mv, macro_ret=macro_ret, etf_ret=etf_ret, etf_or=etf_or)
        names = by_day.get(day, set())
        dayrows = []
        for s, g in S.groupby("symbol"):
            o, h, l, c, v = (g[k].values.astype(float) for k in ("open", "high", "low", "close", "volume"))
            hh = g.h.values
            op = opening(o, h, l, c, v, hh)
            hist = H.setdefault(s, [])
            if live.get(day) and s in names and op is not None:
                ctx.update(rank=ranks.get((day, s), np.nan), dow=day.dayofweek)
                f = stock_row(op, hist, ctx)
                if f is not None:
                    f.update(date=day, symbol=s, r_target=target(o, c, hh))
                    dayrows.append(f)
            e = eod(o, h, l, c, v, hh, close_h)
            if e is not None:
                e.update(date=day, vol_or=op["vol_or"] if op else np.nan, pre_dv=op["pre_dv"] if op else 0.0)
                hist.append(e)
                del hist[:-HIST]
        if dayrows:
            D = pd.DataFrame(dayrows)
            D["mkt_or"] = D.r_or.median(); D["mkt_atr"] = D.atr_pct.median()
            D["rel_or"] = D.r_or - D.mkt_or
            for k in MACRO:
                D[f"m_{k}"] = mv[k]
            D["m_ES_open"] = fut_now.get("ES_open", np.nan)
            D["m_NQ_ES"] = mv["NQ"] - mv["ES"]; D["m_RTY_ES"] = mv["RTY"] - mv["ES"]
            D["m_curve"] = mv["US"] - mv["ZF"]
            # the VX futures level is back-adjusted and drifts; ES realized volatility over
            # the prior 20 sessions stands in for the volatility regime (Amendment 3)
            es = [macro_ret[d].get("ES", np.nan) for d in list(macro_ret)[-20:]]
            D["m_ES_rv20"] = np.nanstd(es) * np.sqrt(252) if np.isfinite(es).sum() >= 15 else np.nan
            D = D.drop(columns=[f"m_{k}" for k in ("NQ", "RTY", "US", "ZF")])
            rows.append(D)
        # roll the references forward
        macro_ret[day] = {k: (fut_close.get(k, np.nan) - macro_prev.get(k, np.nan)) if k == "VX"
                          else lret(fut_close.get(k, np.nan), macro_prev.get(k, np.nan)) for k in MACRO}
        macro_prev = {k: fut_close.get(k, macro_prev.get(k, np.nan)) for k in MACRO}
        etf_ret[day] = {k: lret(etf_cl[k], etf_prev[k]) for k in etf_cl if k in etf_prev}
        etf_prev.update(etf_cl)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main(period="dev"):
    pool = pd.read_parquet("cache/intraday_pool.parquet")
    pool = pool[pool.rk <= 100]
    by_day = {pd.Timestamp(d): set(g) for d, g in pool.groupby("date").symbol}
    ranks = {(pd.Timestamp(r.date), r.symbol): r.rk for r in pool.itertuples()}
    allnames = set(pool.symbol)
    files = {k: {DAY(f): f for f in glob.glob(f"cache/{d}/*.parquet")}
             for k, d in (("stock", "mp5min"), ("etf", "mp_etf_5min"), ("fut", "mp_futures_1min"))}
    days = sorted(files["stock"])
    keep = [d for d in days if d in by_day and ((d < HOLDOUT_START) == (period == "dev"))]
    assert_sealed(keep)
    jobs = []
    for q, ds in pd.Series(keep, index=[d.to_period("Q") for d in keep]).groupby(level=0):
        first = days.index(ds.iloc[0])
        warm = [d for d in days[max(0, first - HIST - 2):first]]
        jobs.append((warm + list(ds), {d: True for d in ds}, by_day, ranks, allnames, files))
    t0 = time.time()
    with Pool(12) as p:
        parts = []
        for i, d in enumerate(p.imap(run_chunk, jobs)):
            parts.append(d)
            print(f"  {i + 1}/{len(jobs)} quarters  {sum(len(x) for x in parts):,} rows  {time.time() - t0:.0f}s", flush=True)
    T = pd.concat(parts, ignore_index=True)
    assert_sealed(T.date)
    out = f"cache/ml_open_{period}.parquet"
    T.to_parquet(out, index=False)
    print(f"{len(T):,} name-days, {T.date.nunique()} sessions, {T.shape[1] - 3} features -> {out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dev")
