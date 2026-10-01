"""EXPLORATORY (development only, 2015 on). Is the FX mean reversion a dollar (time-series)
effect or a cross-sectional one?

Seven currencies' hourly value against USD, from mids (USD itself = 0):
  EUR = eurusd, GBP = gbpusd, AUD = audusd, NZD = nzdusd, JPY = 1/usdjpy,
  CHF = eurusd / eurchf
Split each hour's log returns into
  dollar factor : minus the mean of the six foreign currencies (the USD vs the basket)
  relative      : each currency's return minus the cross-sectional mean of all 7
Strategies, decided at an hour's close, entered 5 minutes later, held H hours (bp,
no costs):
  dollar TS reversal : fade the dollar factor's past L-hour move
  cross-sectional    : weights = -(past L-hour relative return), scaled to unit gross
                       exposure (long the laggards, short the leaders, dollar-neutral)
  cross-sectional, ranked : long the 2 worst, short the 2 best (equal weights)
Reported: mean bp per period, t, and turnover (gross weight change per rebalance,
to estimate costs at about 1 bp per unit traded).

  python3 explore_own/xsection.py
"""
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own")
import data


def currencies():
    m = {p: data.load(p, "dev").mid_close for p in ("eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy", "eurchf")}
    df = pd.DataFrame(m)
    df = df[df.index >= "2015-01-01"].ffill(limit=5)
    c = pd.DataFrame({"EUR": df.eurusd, "GBP": df.gbpusd, "AUD": df.audusd, "NZD": df.nzdusd,
                      "JPY": 1 / df.usdjpy, "CHF": df.eurusd / df.eurchf})
    c["USD"] = 1.0
    return c


def main():
    c = currencies()
    off = c.copy()
    off.index = off.index - pd.Timedelta("5min")             # value 5 minutes after each hour
    h0 = np.log(c.resample("1h", label="right", closed="right").last()).dropna()
    h5 = np.log(off.resample("1h", label="right", closed="right").last()).reindex(h0.index)
    hr = h0.index.hour
    keep = ~((hr >= 16) & (hr <= 19)) & (h0.index.dayofweek < 5)
    ret5 = h5.diff()                                          # hour-to-hour returns, 5-min lagged clock
    rows = []
    for L in (4, 8, 24):
        past = h0.diff(L)
        rel_past = past.sub(past.mean(axis=1), axis=0)
        dollar_past = -past.drop(columns="USD").mean(axis=1)
        for H in (4, 8, 24):
            fut = h5.shift(-H) - h5                           # entry +5 min, hold H hours
            rel_fut = fut.sub(fut.mean(axis=1), axis=0)
            dollar_fut = -fut.drop(columns="USD").mean(axis=1)
            sel = keep & np.arange(len(h0)) % H == 0 if False else keep
            idx = h0.index[sel][::H]                          # non-overlapping rebalances
            w = -rel_past.loc[idx]
            w = w.div(w.abs().sum(axis=1), axis=0)
            xs = (w * rel_fut.loc[idx]).sum(axis=1) * 1e4
            rk = rel_past.loc[idx].rank(axis=1)
            wr = (rk <= 2).astype(float) / 2 - (rk >= 6).astype(float) / 2
            xr = (wr * rel_fut.loc[idx]).sum(axis=1) * 1e4
            dts = -np.sign(dollar_past.loc[idx]) * dollar_fut.loc[idx] * 1e4
            turn = w.diff().abs().sum(axis=1).mean()
            for name, s in (("dollar TS reversal", dts), ("cross-sectional", xs), ("cross-sectional ranked", xr)):
                s = s.dropna()
                rows.append(dict(strategy=name, lookback_h=L, hold_h=H, bp=s.mean(),
                                 t=s.mean() / s.std() * np.sqrt(len(s)), n=len(s),
                                 years_up=f"{(s.groupby(s.index.year).sum() > 0).sum()}/{s.index.year.nunique()}",
                                 turnover=turn if name != "dollar TS reversal" else np.nan))
    out = pd.DataFrame(rows)
    out.to_csv("explore_own/xsection.csv", index=False, float_format="%.3f")
    pd.set_option("display.width", 200)
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
