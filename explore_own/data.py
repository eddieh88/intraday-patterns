"""Spot FX 1-minute bid/ask bars from HistData (data/histdata_fetch.py).

  load(pair, period)  period "dev": 2015 on (development, walk-forward)
                      period "early": before 2015 (final holdout, sealed: EARLY_UNLOCK=final-evaluation)
Returns a frame indexed by New York time (tz-naive, bar start) with bid_*/ask_* OHLC,
mid_* OHLC, spread_mean/spread_max (pips) and ticks. HistData's spread is its
source's all-in retail spread; we trade on it with no extra commission, which
is close to an ECN account's raw spread plus $7 per 100k (see prereg/own_fx.md).
"""
import glob
import pandas as pd
from holdout import EARLY_END, assert_early_sealed


def load(pair, period="dev"):
    files = sorted(glob.glob(f"cache/histdata/{pair}_*.parquet"))
    keep = [f for f in files if (pd.Timestamp(f[-14:-8] + "01") < EARLY_END) == (period == "early")]
    if not keep:
        raise FileNotFoundError(f"no {period} files for {pair}")
    d = pd.concat([pd.read_parquet(f) for f in keep], ignore_index=True)
    if period == "early":
        assert_early_sealed(d.ts_ny)
    d = d.set_index(d.pop("ts_ny").rename("ts")).sort_index()
    d = d[~d.index.duplicated()]
    for c in ("open", "high", "low", "close"):
        d[f"mid_{c}"] = (d[f"bid_{c}"] + d[f"ask_{c}"]) / 2
    if period == "dev":
        d = d[d.index >= EARLY_END]
    return d
