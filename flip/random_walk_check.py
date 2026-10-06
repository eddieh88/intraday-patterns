"""The silent-flip pipeline on random walks, where levels mean nothing by construction.

100 names, 1,071 live sessions after a warm-up, 60 price steps per 5-minute bar
(the path built for structure_stops.md, Amendment 1). The prereg requires real -
fake levels (Q2) and real - random entry (Q3) to be within 2 standard errors of
zero in the primary specification.

  python3 flip/random_walk_check.py      -> exit 0 on PASS, 1 on FAIL
"""
import sys, time
from multiprocessing import Pool

import numpy as np
import pandas as pd

import os
from paths import add_to_path
add_to_path("flip")
import sim
from flip_stats import clustered, clustered_diff, spec_mask, net

SUB = 60                     # price steps per 5-minute bar, as in stops/random_walk_check.py


def walk(rng, p0, sig, n_bars):
    """5-minute OHLC from SUB log steps per bar (sig is per minute). Same as stops/."""
    steps = rng.normal(0, sig * np.sqrt(5 / SUB), size=(n_bars, SUB))
    path = p0 * np.exp(np.cumsum(steps.ravel())).reshape(n_bars, SUB)
    opens = np.r_[p0, path[:-1, -1]]
    hi = np.maximum(path.max(1), opens); lo = np.minimum(path.min(1), opens)
    return opens, hi, lo, path[:, -1], path[-1, -1]

NAMES = int(os.environ.get("RW_NAMES", 100))
VERSION = int(os.environ.get("RW_VERSION", 1))
PRIMARY = sim.PRIMARY if VERSION == 1 else sim.PRIMARY_V2
MONTHS, DAYS, WARM = int(os.environ.get("RW_MONTHS", 51)), 21, sim.LOOKBACK + 3
RTH = 78
HH = 9.5 + np.arange(RTH) * 5 / 60


def run_month(m):
    rng = np.random.default_rng([int(os.environ.get("RW_SEED", 13)), m])
    trade_rng = np.random.default_rng([sim.SEED, int(os.environ.get("RW_SEED", 13)), m])
    sig = np.exp(rng.normal(np.log(0.0009), 0.4, NAMES))
    price = 100 * np.exp(rng.normal(0, 0.8, NAMES))
    hist = {i: [] for i in range(NAMES)}
    rows = []
    for d in range(WARM + DAYS):
        date = pd.Timestamp("2000-01-03") + pd.Timedelta(days=m * 60 + d)
        for i in range(NAMES):
            p = price[i] * np.exp(rng.normal(0, 0.01))
            o, h, l, c, p = walk(rng, p, sig[i], RTH)
            H = hist[i]
            if d >= WARM:
                r, today = sim.name_day(o, h, l, c, HH, H, trade_rng, VERSION)
                for x in r:
                    x["date"], x["symbol"] = date, i
                rows += r
            else:
                _, today = sim.name_day(o, h, l, c, HH, [], trade_rng)
                if len(H) >= 2:
                    today["ratios"] = np.array(sim.levels_from(H, VERSION == 2)) / o[0]
            H.append(today)
            del H[:-(sim.LOOKBACK + 2)]
            price[i] = p
    return rows


def main():
    t0 = time.time()
    with Pool(12) as p:
        rows = [r for month in p.map(run_month, range(MONTHS)) for r in month]
    T = pd.DataFrame(rows)
    T.to_parquet(f"cache/flip{'' if VERSION == 1 else '_v2'}_random_walk_{NAMES}_s{os.environ.get('RW_SEED', 13)}.parquet", index=False)
    x = T[spec_mask(T, PRIMARY)]
    real, fake = x[x.kind == "real"], x[x.kind == "fake"]
    print(f"{len(T):,} random-walk rows; primary: {len(real):,} real and {len(fake):,} fake trades "
          f"over {T.date.nunique()} sessions ({time.time() - t0:.0f}s)\n")
    m, se, t, n = clustered(net(real), real.date)
    print(f"real net R            {m:+.4f} ± {se:.4f}  t {t:+.2f}   (gross {real.R.mean():+.4f})")
    m, se, t, n = clustered(net(fake), fake.date)
    print(f"fake net R            {m:+.4f} ± {se:.4f}  t {t:+.2f}   (gross {fake.R.mean():+.4f})")
    d2, se2, t2 = clustered_diff(net(real), real.date, net(fake), fake.date)
    print(f"Q2 real - fake        {d2:+.4f} ± {se2:.4f}  t {t2:+.2f}")
    m3, se3, t3, _ = clustered(net(real) - net(real, "R_rand", "c_rand"), real.date)
    print(f"Q3 real - random      {m3:+.4f} ± {se3:.4f}  t {t3:+.2f}")
    ok = abs(t2) < 2 and abs(t3) < 2
    print(f"\n{'PASS -- no mechanical bias in Q2 or Q3' if ok else 'FAIL -- the design has a mechanical bias'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
