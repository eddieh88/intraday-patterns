"""EXPLORATORY (development only). What is the pre-cost mean reversion the generator found?

A. Delay: after an hourly event, the mid move from the hour's close + delay to
   close + delay + H, signed so that + means the fade worked, in bp. Quote noise
   reverses within minutes; a real overreaction survives a delay.
     events: down6/up6 (6 hourly closes in a row lower/higher)
             big hour (|hourly return| > 2.5 x its rolling 200-hour sd)
             random hours (the baseline)
B. Weekday drift: mean mid return per hour by weekday, for long-the-base (bp/day).
C. The spread at the event, relative to that pair's median spread.

  python3 explore_own/edge_anatomy.py
"""
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own", "explore_nq")
import data
import mr

PAIRS = ["eurgbp", "eurchf", "audnzd", "eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]
DELAYS, HOLDS = (1, 5, 15, 30, 60), (60, 240)


def main():
    rows, wk, sp_rows = [], [], []
    rng = np.random.default_rng(3)
    for p in PAIRS:
        d = data.load(p, "dev")
        d = d[d.index >= "2015-01-01"]
        mid = d.mid_close
        hc = mid.resample("1h", label="right", closed="right").last().dropna()     # value at the hour's end
        r = hc.pct_change()
        sd = r.rolling(200).std()
        ev = {"down6/up6 (fade)": np.where((r < 0).rolling(6).sum() == 6, 1, np.where((r > 0).rolling(6).sum() == 6, -1, 0)),
              "big hour (fade)": np.where(r < -2.5 * sd, 1, np.where(r > 2.5 * sd, -1, 0))}
        rnd = np.zeros(len(hc), int)
        pick = rng.choice(len(hc), len(hc) // 20, replace=False)
        rnd[pick] = rng.choice([-1, 1], len(pick))
        ev["random hours"] = rnd
        hr = hc.index.hour
        allowed = ~((hr >= 16) & (hr <= 19))                       # skip the rollover, as the generator does
        med_sp = d.spread_mean.median()
        for name, side in ev.items():
            t = hc.index[(side != 0) & allowed]
            s = side[(side != 0) & allowed]
            row = dict(pair=p, event=name, n=len(t))
            for dl in DELAYS:
                a = mid.reindex(t + pd.Timedelta(minutes=dl), method="ffill").values
                for H in HOLDS:
                    b = mid.reindex(t + pd.Timedelta(minutes=dl + H), method="ffill").values
                    row[f"d{dl}_h{H}"] = np.nanmean(s * (b / a - 1) * 1e4)
            spr = d.spread_mean.reindex(t - pd.Timedelta(minutes=1), method="ffill").values
            row["spread_vs_median"] = np.nanmedian(spr) / med_sp
            rows.append(row)
        dr = mid.resample("1h").last().pct_change() * 1e4
        wk.append(dr.groupby(dr.index.dayofweek).mean().rename(p) * 24)
    out = pd.DataFrame(rows)
    out.to_csv("explore_own/edge_anatomy.csv", index=False, float_format="%.3f")
    pd.set_option("display.width", 230)
    cols = [c for c in out.columns if c.startswith("d")]
    print("A. Fade return after the event (bp, mean over pairs), by entry delay and hold:")
    print(out.groupby("event")[cols + ["spread_vs_median"]].mean().round(2).to_string())
    print("\n   per pair, big hour, 1-minute delay, 60-min hold:")
    print(out[out.event == "big hour (fade)"].set_index("pair")[["n", "d1_h60", "d15_h60", "d60_h60", "spread_vs_median"]].round(2).to_string())
    w = pd.DataFrame(wk).rename(columns=dict(enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])))
    print("\nB. Mean move per day by weekday, long the base currency (bp/day):")
    print(w.round(1).to_string())


if __name__ == "__main__":
    main()
