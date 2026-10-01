"""EXPLORATORY (development only, 2015 on). Which part of a multi-hour run reverses:
the dollar, or one currency against the rest?

Uses xsection.currencies() (7 currencies vs USD, from mids), on the hourly clock, with
entries 5 minutes after the hour. Events (6 hourly moves in a row in one direction,
outside 16:00-19:59 New York and weekends):
  dollar run    : the dollar factor (USD vs the average of the 6) ran 6 hours
                  -> fade the dollar factor
  relative run  : one currency's relative return (vs the 7-currency mean) ran 6 hours
                  -> fade that currency's relative value
  pair run      : the pair itself ran (as in weekday_runs.py). Its fade splits
                  exactly into a dollar part (the 6 foreign currencies' mean vs USD)
                  and the currency's deviation from the other foreign currencies
Returns are bp over 1, 4, 8 and 24 hours. Hourly currency logs are cached in
cache/own_ccy_hourly.parquet.

  python3 explore_own/run_decompose.py
"""
import os
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own")

CACHE = "cache/own_ccy_hourly.parquet"


def hourly():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    import xsection
    c = xsection.currencies()
    off = c.copy()
    off.index = off.index - pd.Timedelta("5min")
    h0 = np.log(c.resample("1h", label="right", closed="right").last()).dropna()
    h5 = np.log(off.resample("1h", label="right", closed="right").last()).reindex(h0.index)
    out = pd.concat({"close": h0, "entry": h5}, axis=1)
    out.to_parquet(CACHE)
    return out


def runs(r, n=6):
    up = (r > 0).astype(int).rolling(n).sum() == n
    dn = (r < 0).astype(int).rolling(n).sum() == n
    return np.where(dn, 1, np.where(up, -1, 0))          # +1 = fade a down run (buy)


def main():
    H = hourly()
    H = H[~((H.index >= "2015-01-15") & (H.index < "2015-01-16"))]   # the SNB de-peg day
    c0, c5 = H["close"], H["entry"]
    hr = c0.index.hour
    ok = ~((hr >= 16) & (hr <= 19)) & (c0.index.dayofweek < 5)
    foreign = [x for x in c0.columns if x != "USD"]
    # skipna=False: a missing currency must not change which currencies the mean
    # averages (log levels differ by ~5 between JPY and EUR; dropping one jumps the mean)
    dollar0 = -c0[foreign].mean(axis=1, skipna=False)
    dollar5 = -c5[foreign].mean(axis=1, skipna=False)
    rel0 = c0.sub(c0.mean(axis=1, skipna=False), axis=0)
    rel5 = c5.sub(c5.mean(axis=1, skipna=False), axis=0)
    rows = []

    def add(name, side, fwd_series_list):
        m = (side != 0) & ok
        row = dict(event=name, n=int(m.sum()))
        for h in (1, 4, 8, 24):
            vals = [s * (x.shift(-h) - x).values * 1e4 for s, x in fwd_series_list]
            v = sum(vals)[m] if len(vals) > 1 else vals[0][m]
            row[f"h{h}"] = np.nanmean(v)
            if h == 8:
                row["t8"] = np.nanmean(v) / (np.nanstd(v) / np.sqrt(np.sum(~np.isnan(v))))
        rows.append(row)

    sd = runs(dollar0.diff())
    add("dollar run -> fade the dollar", sd, [(sd, dollar5)])
    for ccy in c0.columns:
        s = runs(rel0[ccy].diff())
        add(f"relative run {ccy} -> fade {ccy} vs the rest", s, [(s, rel5[ccy])])
    for ccy in foreign:
        s = runs(c0[ccy].diff())                         # the pair vs USD ran
        add(f"pair run {ccy}USD -> fade pair, total", s, [(s, c5[ccy])])
        add(f"   of which the dollar part", s, [(s, -dollar5)])
        add(f"   of which {ccy} vs the other foreign", s, [(s, c5[ccy] + dollar5)])
    out = pd.DataFrame(rows)
    out.to_csv("explore_own/run_decompose.csv", index=False, float_format="%.3f")
    pd.set_option("display.width", 200)
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
