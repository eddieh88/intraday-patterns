"""EXPLORATORY (development only, 2015 on). Two follow-ups from edge_anatomy.py.

1. Weekday risk pattern. Each FX day runs 17:00-17:00 New York, named by the day it
   ends on. A "risk-on" basket is long AUD, NZD, GBP, EUR vs USD, long USD vs JPY,
   long EUR vs CHF, and long AUD vs NZD (each pair long its base). Reported: the
   basket's mid return per FX day by weekday and year, its t-stat, and the net of
   one round-trip spread per pair.
2. The run-fade at longer holds: after 6 hourly closes in a row, the faded mid return
   from close + 5 minutes over 1, 4, 8 and 24 hours (bp, mean over pairs).

  python3 explore_own/weekday_runs.py
"""
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own")
import data

PAIRS = ["eurgbp", "eurchf", "audnzd", "eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]


def main():
    day_ret, spreads, runs = {}, {}, []
    for p in PAIRS:
        d = data.load(p, "dev")
        d = d[d.index >= "2015-01-01"]
        mid = d.mid_close
        fxday = (mid.index + pd.Timedelta("7h")).normalize()
        last = mid.groupby(fxday).last()
        day_ret[p] = last.pct_change() * 1e4
        spreads[p] = float(((d.ask_close - d.bid_close) / mid).median() * 1e4)
        hc = mid.resample("1h", label="right", closed="right").last().dropna()
        r = hc.pct_change()
        side = np.where((r < 0).rolling(6).sum() == 6, 1, np.where((r > 0).rolling(6).sum() == 6, -1, 0))
        hr = hc.index.hour
        m = (side != 0) & ~((hr >= 16) & (hr <= 19))
        t, s = hc.index[m], side[m]
        a = mid.reindex(t + pd.Timedelta("5min"), method="ffill").values
        row = {"pair": p, "events": len(t), "spread_bp": spreads[p]}
        for H in (1, 4, 8, 24):
            b = mid.reindex(t + pd.Timedelta(minutes=5 + 60 * H), method="ffill").values
            row[f"h{H}"] = np.nanmean(s * (b / a - 1) * 1e4)
        runs.append(row)
    R = pd.DataFrame(day_ret).dropna(how="all")
    R = R[R.index.dayofweek < 5]
    basket = R.mean(axis=1)
    cost = np.mean(list(spreads.values()))
    pd.set_option("display.width", 200)
    names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    g = basket.groupby(basket.index.dayofweek)
    print("1. Risk-on basket, mean mid return per FX day (bp), by weekday:")
    tab = pd.DataFrame({"mean": g.mean(), "t": g.mean() / (g.std() / np.sqrt(g.size())), "days": g.size()})
    tab.index = names
    print(tab.round(2).to_string())
    print(f"   average round-trip spread per pair: {cost:.2f} bp")
    yr = basket.groupby([basket.index.year, basket.index.dayofweek]).mean().unstack()
    yr.columns = names
    print("\n   by year (bp per FX day):")
    print(yr.round(1).to_string())
    ls = basket.where(basket.index.dayofweek == 0, 0) - basket.where(basket.index.dayofweek.isin([3, 4]), 0)
    trade_days = basket.index.dayofweek.isin([0, 3, 4])
    net = ls[trade_days] - cost
    print(f"\n   'risk-on Monday, risk-off Thursday+Friday': {net.mean():+.2f} bp per trading day net of spread, "
          f"t {net.mean() / (net.std() / np.sqrt(len(net))):+.2f}, years positive "
          f"{(net.groupby(net.index.year).sum() > 0).sum()}/{net.index.year.nunique()}")
    print("\n2. Run-fade by hold (bp, entry 5 min after the 6th close):")
    print(pd.DataFrame(runs).set_index("pair").round(2).to_string())
    print(pd.DataFrame(runs)[["h1", "h4", "h8", "h24"]].mean().round(2).to_string())


if __name__ == "__main__":
    main()
