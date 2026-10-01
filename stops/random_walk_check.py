"""The whole pipeline on random walks, where structure means nothing by construction.

Simulated sessions match development in shape: 100 names a day, the same number of
sessions, 78 RTH bars after 66 pre-market bars, per-name volatility spread like
real large caps, and an overnight gap. Each 5-minute bar is built from SUB
price steps (60 by default). The prereg requires S - C to be within 2 standard errors of zero
for every setup; anything else is a mechanical bias to fix before real data.

  python3 stops/random_walk_check.py      -> exit 0 on PASS, 1 on FAIL
"""
import os, sys, time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("stops")
import sim
from stats import clustered, net, cell

NAMES, MONTHS, DAYS = 100, int(os.environ.get("RW_MONTHS", 51)), 21    # 1,071 sessions; development has 1,055
# Price steps per 5-minute bar. 5 (one a minute) failed the check: price jumped past
# stops yet filled at them, which flatters tight stops. 60 matches liquid names, which
# trade many times a minute. See Amendment 1 in the prereg. RW_SUB=5 reproduces the failure.
SUB = int(os.environ.get("RW_SUB", 60))
PRE, RTH = 66, 78                           # 04:00-09:25 and 09:30-15:55
HH = 9.5 + np.arange(RTH) * 5 / 60


def walk(rng, p0, sig, n_bars):
    """5-minute OHLC from SUB log steps per bar. Returns (o, h, l, c), last price."""
    steps = rng.normal(0, sig * np.sqrt(5 / SUB), size=(n_bars, SUB))
    path = p0 * np.exp(np.cumsum(steps.ravel())).reshape(n_bars, SUB)
    opens = np.r_[p0, path[:-1, -1]]
    hi = np.maximum(path.max(1), opens); lo = np.minimum(path.min(1), opens)
    return opens, hi, lo, path[:, -1], path[-1, -1]


def run_month(m):
    rng = np.random.default_rng([11, m])
    sig = np.exp(rng.normal(np.log(0.0009), 0.4, NAMES))       # per 1-minute step
    price = 100 * np.exp(rng.normal(0, 0.8, NAMES))
    tails = {}
    trades = []
    for d in range(DAYS + 1):                                   # day 0 only seeds the tails
        date = pd.Timestamp("2000-01-03") + pd.Timedelta(days=m * 40 + d)
        for i in range(NAMES):
            p = price[i] * np.exp(rng.normal(0, 0.01))          # overnight gap
            po, ph, pl, pc, p = walk(rng, p, 0.4 * sig[i], PRE)
            o, h, l, c, p = walk(rng, p, sig[i], RTH)
            v = np.exp(rng.normal(8, 0.5, RTH))
            if d and i in tails:
                tr, pdh, pdl = tails[i]
                for t in sim.session_trades(o, h, l, c, v, HH, ph, pl, tr, pdh, pdl):
                    t["date"], t["symbol"] = date, i
                    trades.append(t)
            tails[i] = ((h - l)[-sim.ATR_N:], h.max(), l.min())
            price[i] = p
    rows = sim.score_month(trades, np.random.default_rng([sim.SEED, m]))
    for r, t in zip(rows, trades):
        r["date"], r["symbol"] = t["date"], t["symbol"]
    return rows


def main():
    t0 = time.time()
    with Pool(12) as p:
        rows = [r for month in p.map(run_month, range(MONTHS)) for r in month]
    T = pd.DataFrame(rows)
    T.to_parquet(f"cache/stops_random_walk_sub{SUB}.parquet", index=False)
    print(f"{len(T):,} random-walk trades over {T.date.nunique()} sessions ({time.time() - t0:.0f}s)\n")
    ok = True
    print(f"{'setup':10s}{'cell':>10s}{'n':>9s}{'S - C @3bp':>12s}{'se':>8s}{'t':>7s}{'S gross':>9s}{'C gross':>9s}")
    for s in sim.SETUPS:
        x = T[T.setup == s]
        for b in sim.BUFFERS:
            for k in sim.TARGETS:
                c = cell(b, k)
                d = net(x, f"S_{c}", 3) - net(x, f"C_{c}", 3)
                m, se, t, n = clustered(d, x.date)
                prim = (b, k) == (sim.PRIMARY_B, sim.PRIMARY_T)
                print(f"{s:10s}{c:>10s}{n:9,}{m:+12.4f}{se:8.4f}{t:+7.2f}"
                      f"{x[f'R_S_{c}'].mean():+9.4f}{x[f'R_C_{c}'].mean():+9.4f}{'  <- primary' if prim else ''}")
                if prim and not abs(t) < 2:
                    ok = False
    print(f"\n{'PASS -- S and C tie on random walks' if ok else 'FAIL -- the design has a mechanical bias'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
