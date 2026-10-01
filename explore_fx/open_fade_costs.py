"""EXPLORATORY. The 19:00 New York previous-close fade (open_fade_match.py, modes at_19 and
touch_19), re-costed at ECN execution instead of HistData's retail spreads: simulate at the
mid (bid = ask = mid), then charge a per-pair round-trip cost in pips:
  ecn   : raw spread + $7 per 100k round trip (0.7 pip on USD-quoted pairs)
          EURUSD 0.8, GBPUSD 1.0, AUDUSD 0.9, NZDUSD 1.1, USDJPY 0.9 pips
  limit : a limit-order entry pays no spread on entry: half the raw spread + commission
          EURUSD 0.75, GBPUSD 0.85, AUDUSD 0.8, NZDUSD 0.9, USDJPY 0.8 pips
His own spread cap is already in the entry rule (open_fade_match's spread filter).

  python3 explore_fx/open_fade_costs.py -> explore_fx/open_fade_costs.csv
"""
import itertools
import multiprocessing as mp
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_fx")
import data
import open_fade_match as O
from weekend_match import his_fingerprints, score, START, END

COST = {"ecn": {"eurusd": 0.8, "gbpusd": 1.0, "audusd": 0.9, "nzdusd": 1.1, "usdjpy": 0.9},
        "limit": {"eurusd": 0.75, "gbpusd": 0.85, "audusd": 0.8, "nzdusd": 0.9, "usdjpy": 0.8}}
USD_PAIRS = ["eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]
_load = data.load


def mid_load(pair, period="dev"):
    d = _load(pair, period)
    for side in ("bid", "ask"):
        for c in ("open", "high", "low", "close"):
            d[f"{side}_{c}"] = d[f"mid_{c}"]
    return d


def run(pair):
    data.load = mid_load
    O.data.load = mid_load
    O.MODES = ("touch_19", "at_19")
    df = O.run_pair(pair)
    return df[df["mode"].isin(["touch_19", "at_19"])]


if __name__ == "__main__":
    with mp.get_context("fork").Pool(5) as pool:
        trades = pd.concat(pool.map(run, USD_PAIRS), ignore_index=True)
    px = {p: float(_load(p, "dev").mid_close.median()) for p in USD_PAIRS}
    iv, his_rate, his_q = his_fingerprints()
    out = []
    for cost_name, cost in COST.items():
        t = trades.copy()
        c = t.pair.map(cost)
        t["pips"] = t.pips - c
        t["bp"] = t.bp - c * t.pair.map(O.PIP) / t.pair.map(px) * 1e4
        for key, g0 in t.groupby(["mode", "X", "S", "rr", "H"]):
            for trio in itertools.combinations(USD_PAIRS, 3):
                g = g0[g0.pair.isin(trio)]
                if len(g) < 30:
                    continue
                r = score(g, iv, his_rate, his_q)
                out.append(dict(costs=cost_name, mode=key[0], X=key[1], S=key[2], rr=key[3], H=key[4],
                                trio="+".join(trio), **r))
    res = pd.DataFrame(out)
    res.to_csv("explore_fx/open_fade_costs.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    print(res.groupby(["costs", "mode"])[["ret_dd", "win", "weekday_loglik", "mon_share", "timing", "pnl_corr"]].median().round(2).to_string())
    for cn in COST:
        s = res[res.costs == cn].sort_values("ret_dd", ascending=False)
        print(f"\n{cn}: best by return/drawdown")
        print(s[["mode", "X", "S", "rr", "H", "trio", "trades", "win", "bp", "weekday_loglik", "mon_share", "timing", "pnl_corr", "ret_dd"]].head(8).round(2).to_string(index=False))
