"""EXPLORATORY. What does NQ do after the posted system's dip fills, with no target,
stop or one-position rule in the way? Development period only.

Every 3-minute close from 10:03 to 11:57 New York is a candidate. A "dip" is the
limit at close - k x ATR trading 1 tick through within 9 minutes. From the fill
price, we measure the move to the open h minutes after the fill minute, in ATRs.
The baseline is the same h-minute move from every minute of the window. A "rip"
is the mirror image (a short limit above the close), with its move signed so
that + means the fade worked.

  python3 explore_nq/events.py [SYMBOL]
"""
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_nq")
import mr

H = (1, 3, 5, 10, 15, 30, 60)


def events(m1, k=1.0, tick=mr.TICK):
    b = mr.bars3(m1)
    b = b.assign(er=mr.efficiency_ratio(b.close), atr=mr.atr(b))
    close_t = b.index + pd.Timedelta("3min")
    tod = close_t.time
    b = b[(tod > pd.Timestamp("10:00").time()) & (tod < pd.Timestamp("12:00").time())]
    c = b.index + pd.Timedelta("3min")
    lows = np.column_stack([m1.low.reindex(c + pd.Timedelta(minutes=j)).values for j in range(9)])
    highs = np.column_stack([m1.high.reindex(c + pd.Timedelta(minutes=j)).values for j in range(9)])
    out = []
    for side, ext, lvl in ((1, lows, b.close.values - k * b.atr.values),
                           (-1, highs, b.close.values + k * b.atr.values)):
        hit = side * (lvl[:, None] - side * tick - ext) >= 0
        filled = hit.any(1)
        first = hit.argmax(1)
        tf = c + pd.to_timedelta(first, unit="min")
        d = pd.DataFrame({"side": side, "sig": b.index, "fill_t": tf, "px": lvl, "atr": b.atr.values,
                          "er": b.er.values})[filled]
        for h in H:
            fwd = m1.open.reindex(pd.DatetimeIndex(d.fill_t) + pd.Timedelta(minutes=h + 1)).values
            d[f"r{h}"] = side * (fwd - d.px.values) / d.atr.values
        out.append(d)
    return pd.concat(out, ignore_index=True)


def baseline(m1):
    """The h-minute move from every minute of 10:03-11:57, in 3-minute ATRs."""
    b = mr.bars3(m1)
    a = mr.atr(b).reindex(m1.index, method="ffill").shift(3)
    w = m1[(m1.index.time > pd.Timestamp("10:02").time()) & (m1.index.time < pd.Timestamp("11:58").time())]
    return {h: np.nanmean((m1.open.shift(-h).reindex(w.index) - w.open) / a.reindex(w.index)) for h in H}


def table(d, base, by=None):
    cols = [f"r{h}" for h in H]
    g = d.groupby(by) if by else d.groupby(lambda _: "all")
    t = g[cols].mean()
    t.insert(0, "n", g.size())
    return t


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "NQ"
    m1 = mr.load_nq("dev", sym)
    base = baseline(m1)
    pd.set_option("display.width", 200)
    print(f"{sym} development. Mean move after the fill, in ATRs (+ = the fade worked)")
    print("any minute (long):  " + "  ".join(f"{h}m {base[h]:+.3f}" for h in H))
    for k in (0.5, 1.0, 1.5):
        d = events(m1, k)
        d["er_bin"] = pd.cut(d.er, [0, 0.2, 0.35, 0.5, 1], labels=["<.2", ".2-.35", ".35-.5", ">.5"])
        d["year"] = d.sig.dt.year
        print(f"\n--- k = {k} ATR ---")
        print(table(d, base, "side").round(3).rename(index={1: "dip, long", -1: "rip, short"}))
        print(table(d[d.side == 1], base, "er_bin").round(3))
        print(table(d[d.side == 1], base, "year").round(3))
