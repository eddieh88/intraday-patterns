"""Feature study for the silent flip v2 (prereg/silent_flip_v2.md, "Feature study").

Does anything known by 10:00 pick the trades that pay? Six features, cut into
fifths at the real trades' quintiles; real, fake and real - fake per fifth.
Development only.

  python3 flip/features.py
"""
import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("flip")
import sim
from flip_stats import clustered, clustered_diff, spec_mask, net
from holdout import HOLDOUT_START

FEATURES = ["vol_regime", "yday_width", "gap", "open_range", "mkt_with", "mkt_vol"]


def daily_features():
    D = pd.read_parquet("cache/intraday_daily.parquet",
                        columns=["symbol", "date", "o_or", "c_or", "hi_or", "lo_or", "hi_open", "lo_open",
                                 "hi_rth", "lo_rth", "c_rth"]).sort_values(["symbol", "date"])
    D = D[D.date < HOLDOUT_START + pd.Timedelta(days=1)]                  # nothing after development is read
    # full-session high/low: the table's *_rth columns are 11:00-16:00 only
    D["hi"] = D[["hi_or", "hi_open", "hi_rth"]].max(axis=1)
    D["lo"] = D[["lo_or", "lo_open", "lo_rth"]].min(axis=1)
    D["rng"] = D.hi - D.lo
    g = D.groupby("symbol")
    prev = lambda s: g[s].shift(1)
    D["atr20"] = g.rng.transform(lambda x: x.shift(1).rolling(20, min_periods=15).mean())
    D["atr5"] = g.rng.transform(lambda x: x.shift(1).rolling(5, min_periods=5).mean())
    D["or_rng"] = D.hi_or - D.lo_or
    D["or20"] = g.or_rng.transform(lambda x: x.shift(1).rolling(20, min_periods=15).mean())
    D["vol_regime"] = D.atr5 / D.atr20
    D["yday_width"] = (prev("hi") - prev("lo")) / D.atr20
    D["gap"] = (D.o_or - prev("c_rth")).abs() / D.atr20
    D["open_range"] = D.or_rng / D.or20
    # market: the day's point-in-time top 100
    pool = pd.read_parquet("cache/intraday_pool.parquet")
    pool = pool[pool.rk <= 100][["date", "symbol"]]
    M = D.merge(pool, on=["date", "symbol"])
    mk = M.assign(r=M.c_or / M.o_or - 1, rv=M.rng / M.c_rth).groupby("date").agg(mkt=("r", "median"), rv=("rv", "median"))
    mk["mkt_vol"] = mk.rv.shift(1).rolling(20, min_periods=15).mean()
    D = D.merge(mk[["mkt", "mkt_vol"]], left_on="date", right_index=True, how="left")
    return D[["symbol", "date", "vol_regime", "yday_width", "gap", "open_range", "mkt", "mkt_vol"]]


def main():
    T = pd.read_parquet("cache/flip_v2_dev.parquet")
    T = T[spec_mask(T, sim.PRIMARY_V2)].copy()
    T["net"] = net(T)
    T = T.merge(daily_features(), on=["symbol", "date"], how="left")
    T["mkt_with"] = T.side * T.mkt
    T["block"] = np.minimum(T.date.dt.year, 2024)
    real, fake = T[T.kind == "real"], T[T.kind == "fake"]
    print(f"{len(real):,} real and {len(fake):,} fake trades; net R at 3 bp\n")
    hits = []
    for f in FEATURES:
        cuts = np.nanquantile(real[f], [.2, .4, .6, .8])
        bins = [-np.inf, *cuts, np.inf]
        print(f"{f}  (fifth edges {', '.join(f'{c:.3g}' for c in cuts)}; missing real {real[f].isna().mean():.0%})")
        for q in range(5):
            r = real[(real[f] > bins[q]) & (real[f] <= bins[q + 1])]
            k = fake[(fake[f] > bins[q]) & (fake[f] <= bins[q + 1])]
            m, se, t, n = clustered(r.net, r.date)
            d, _, td = clustered_diff(r.net, r.date, k.net, k.date)
            yrs = r.groupby("block").net.mean()
            pos = int((yrs > 0).sum())
            ok = t >= 3.0 and d > 0 and td >= 2.0 and pos >= 3
            hits += [(f, q + 1)] if ok else []
            print(f"   Q{q + 1}  real n {n:4d}  net {m:+.4f} (t {t:+.2f})  fake {k.net.mean():+.4f}  "
                  f"real-fake {d:+.4f} (t {td:+.2f})  years +{pos}/4{'   QUALIFIES' if ok else ''}")
    print(f"\nqualifying cells: {hits if hits else 'none'}")


if __name__ == "__main__":
    main()
