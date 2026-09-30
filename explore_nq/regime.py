"""EXPLORATORY. Does the posted system work in sideways ("crab") markets? Development
period only.

The posted filter looks at the last 45 minutes. Here the regime is measured at
longer scales:
  hindsight : how sideways the 10:00-12:00 window turned out (efficiency ratio of its
              1-minute closes). Not tradable, and biased toward the strategy, because
              a window that ends flat is one where dips came back.
  ex ante   : known before the trade.
              - daily efficiency ratio over the prior 10 and 20 sessions (16:00 closes)
              - daily ADX(14)
              - the day so far: efficiency ratio of 1-minute closes from 09:30 to the fill
Each measure is cut into quintiles. For each quintile we report the posted system
(gross and net ATR per trade) and the event study's 15-minute move after a dip fill.

  python3 explore_nq/regime.py
"""
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_nq")
import mr, events


def daily(m1):
    rth = m1.between_time("09:30", "15:59")
    return rth.groupby(rth.index.normalize()).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))


def adx(d, n=14):
    up, dn = d.high.diff(), -d.low.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = d.close.shift()
    tr = pd.concat([d.high - d.low, (d.high - pc).abs(), (d.low - pc).abs()], axis=1).max(axis=1)
    sm = lambda x: pd.Series(x, index=d.index).ewm(alpha=1 / n, adjust=False).mean()
    atr_ = sm(tr)
    pdi, ndi = 100 * sm(pdm) / atr_, 100 * sm(ndm) / atr_
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def session_er(m1, times):
    """Efficiency ratio of 1-minute closes from 09:30 up to each time (exclusive)."""
    c = m1.close
    out = []
    for t in times:
        x = c[t.normalize() + pd.Timedelta("09:30:00"):t - pd.Timedelta("1min")].values
        out.append(abs(x[-1] - x[0]) / np.abs(np.diff(x)).sum() if len(x) > 2 else np.nan)
    return np.array(out)


def window_er(m1):
    w = m1.between_time("10:00", "11:59").close
    g = w.groupby(w.index.normalize())
    return g.apply(lambda x: abs(x.iloc[-1] - x.iloc[0]) / np.abs(np.diff(x.values)).sum())


def by_quintile(df, col, val):
    q = pd.qcut(df[col], 5, labels=["Q1 sideways", "Q2", "Q3", "Q4", "Q5 trending"])
    g = df.groupby(q, observed=True)[val]
    return g.mean(), g.size()


if __name__ == "__main__":
    m1 = mr.load_nq("dev")
    tr = mr.simulate(m1, mr.bars3(m1))
    tr["gross"] = tr.pts / tr.atr
    tr["net"] = tr.pts_net / tr.atr
    ev = events.events(m1, 1.0)
    ev = ev[ev.side == 1].copy()
    ev["day"] = ev.sig.dt.normalize()

    d = daily(m1)
    reg = pd.DataFrame({
        "daily ER 10d": mr.efficiency_ratio(d.close, 10).shift(),
        "daily ER 20d": mr.efficiency_ratio(d.close, 20).shift(),
        "daily ADX 14": adx(d).shift(),
        "HINDSIGHT window ER": window_er(m1),
    })
    tr = tr.join(reg, on="day")
    ev = ev.join(reg, on="day")
    tr["session ER so far"] = session_er(m1, tr.fill_t)
    ev["session ER so far"] = session_er(m1, pd.DatetimeIndex(ev.fill_t))

    pd.set_option("display.width", 200)
    for col in ["HINDSIGHT window ER", "daily ER 10d", "daily ER 20d", "daily ADX 14", "session ER so far"]:
        g, n = by_quintile(tr, col, "gross")
        ne, _ = by_quintile(tr, col, "net")
        r15, ne2 = by_quintile(ev, col, "r15")
        lo, hi = tr[col].quantile([0.2, 0.8])
        print(f"\n{col}  (20th pct {lo:.2f}, 80th pct {hi:.2f})")
        print(pd.DataFrame({"trades": n, "gross ATR/trade": g, "net ATR/trade": ne,
                            "dips": ne2, "15-min move after dip": r15}).round(3).to_string())
