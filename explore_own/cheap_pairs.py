"""EXPLORATORY (development only). The ideas that persist before costs (gen_run.py
persistence on *_gross: median-over-exits Sharpe > 0 in both 2015-2020 and 2021-2026,
top 15 by OOS), traded WITH real bid/ask costs on the cheapest pairs only. The pairs
are chosen by spread, not by results: EURUSD and USDJPY have median spreads under
0.5 bp; GBPUSD (~0.6 bp) is reported on its own.

For each idea, all 60 exit settings are run. Reported: medians over exits of net
Sharpe (monthly), net bp/trade, and years positive, for each half.

  python3 explore_own/cheap_pairs.py
"""
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_own")
import data
import generator as g
import gen_run as G

IDEAS = ["down6bars|mr|afternoon|both", "new_low50|mr|trend_up|long", "bb50_out|mr|monday|both",
         "new_low50|mr|monday|long", "rsi2<10|mr|monday|long", "below_sma200|mr|monday|long",
         "new_low50|mr|monday|both", "rsi14<30|mr|monday|long", "new_low10|mr|monday|long",
         "rsi5<25|mr|monday|long", "bb50_out|mr|monday|long", "down6bars|mr|afternoon|short",
         "bb20_out|mr|monday|long", "rsi14<30|mr|trend_down|short", "new_low20|mr|monday|long"]
GROUPS = {"EURUSD+USDJPY": ["eurusd", "usdjpy"], "GBPUSD": ["gbpusd"]}


def main():
    split = (G.IS_END - G.START).n + 1
    cache = {}
    for p in {x for v in GROUPS.values() for x in v}:
        h = g.hourly(data.load(p, "dev"))
        h = h[h.index >= G.START.start_time]
        sig, fil, atr = g.blocks(h)
        A = g.prepare(h)
        A["atr"], A["month"] = atr, np.asarray((h.index.to_period("M") - G.START).map(lambda x: x.n), np.int64)
        cache[p] = (sig, fil, A)
    sig, fil, _ = cache["eurusd"]
    sname, fname = [s[0] for s in sig], [f[0] for f in fil]
    n_months = max(int(A["month"].max()) for *_, A in cache.values()) + 1
    rows = []
    for grp, pairs in GROUPS.items():
        for idea in IDEAS:
            s_, dirn, f_, mode = idea.split("|")
            si, fi, md = sname.index(s_), fname.index(f_), g.MODES.index(mode)
            per = []
            for a in g.STOPS:
                for b in g.TARGETS:
                    for hold in g.HOLDS:
                        out = np.zeros((n_months, 3))
                        for p in pairs:
                            sg, fl, A = cache[p]
                            lo, sh = sg[si][1], sg[si][2]
                            if dirn == "mom":
                                lo, sh = sh, lo
                            m = fl[fi][1]
                            gl = lo & m if md in (0, 2) else np.zeros_like(m)
                            gs = sh & m if md in (1, 2) else np.zeros_like(m)
                            g.run_one(gl, gs, A["atr"], A["bo"], A["bh"], A["bl"], A["bc"], A["ao"], A["ah"],
                                      A["al"], A["ac"], A["mid_o"], A["ok"], A["fri_end"], A["month"], a, b, hold, out)
                        r = {}
                        for half, sl in (("IS", slice(0, split)), ("OOS", slice(split, n_months))):
                            s, n = out[sl, 0], out[sl, 1]
                            r[f"{half}_bp"] = s.sum() / max(n.sum(), 1)
                            r[f"{half}_sh"] = s.mean() / s.std() * np.sqrt(12) if s.std() else 0
                            r[f"{half}_n"] = n.sum()
                        yr = out[:, 0][: (n_months // 12) * 12].reshape(-1, 12).sum(1)
                        r["years_up"] = (yr > 0).sum()
                        r["years"] = len(yr)
                        per.append(r)
            d = pd.DataFrame(per)
            rows.append(dict(group=grp, idea=idea, IS_sh=d.IS_sh.median(), OOS_sh=d.OOS_sh.median(),
                             IS_bp=d.IS_bp.median(), OOS_bp=d.OOS_bp.median(),
                             trades_per_yr=(d.IS_n.median() + d.OOS_n.median()) / (n_months / 12),
                             exits_pos_both=np.mean((d.IS_sh > 0) & (d.OOS_sh > 0)),
                             years_up=f"{int(d.years_up.median())}/{int(d.years.iloc[0])}"))
    out = pd.DataFrame(rows)
    out.to_csv("explore_own/cheap_pairs.csv", index=False, float_format="%.3f")
    pd.set_option("display.width", 220)
    print(out.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
