"""A night-scalper test on three synthetic FX crosses. Rules are frozen in
prereg/fx_night_scalper.md.

  crosses : EURGBP = E6/B6, AUDNZD = A6/N6, EURCHF = E6/E1. Each is built only from
            minutes where both legs traded (no forward fill), so a stale leg can't
            fake a jump and a reversal.
  bars    : 5-minute bars from those 1-minute cross prices; Bollinger(20, 2) on the closes
  entries : from a 5-minute bar closing 18:15-01:00 New York (Sunday-Thursday nights).
            A close above the upper band -> short; below the lower band -> long.
            Entry is at the first both-traded minute's close, at least `delay` minutes
            after the bar closes
  target  : the signal bar's middle band, exited at the first 1-minute close through it
  stop    : 2 x the entry's distance from the target, on the other side, exited at the
            first 1-minute close beyond it
  time    : flat at the first minute at or after 02:00 New York (before Frankfurt/London)
  costs   : spot-like round trips: EURGBP 1.7 bp, AUDNZD 2.8 bp, EURCHF 2.1 bp
            (1.5 / 3 / 2 pips)
One position per cross. Returns are in bp of price.

  python3 explore_fx/night.py [holdout]
"""
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_nq")
import mr

CROSSES = {"EURGBP": ("E6", "B6", 1.7), "AUDNZD": ("A6", "N6", 2.8), "EURCHF": ("E6", "E1", 2.1)}


def cross(a, b):
    """1-minute cross prices, from minutes where both legs traded."""
    return (a.close / b.close).dropna()


def bars5(px):
    return px.resample("5min", label="left", closed="left").agg(["first", "max", "min", "last"]).dropna().rename(
        columns={"first": "open", "max": "high", "min": "low", "last": "close"})


def night_of(t):
    """The FX session a time belongs to (the New York date on which it ends at 17:00)."""
    return (t + pd.Timedelta("7h")).normalize()


def simulate(px, n=20, k=2.0, stop_mult=2.0, delay=1, cost_bp=0.0,
             start="18:15", last_entry="01:00", flat="02:00"):
    b = bars5(px)
    mid = b.close.rolling(n).mean()
    sd = b.close.rolling(n).std()
    close_t = b.index + pd.Timedelta("5min")
    tod = close_t.time
    s, e = pd.Timestamp(start).time(), pd.Timestamp(last_entry).time()
    in_win = (tod >= s) | (tod <= e)
    dow = close_t.dayofweek
    night_ok = np.where(pd.Index(tod) >= s, dow <= 3, (dow >= 0) & (dow <= 4)) | (dow == 6)
    side = np.where(b.close > mid + k * sd, -1, np.where(b.close < mid - k * sd, 1, 0))
    sig = pd.DataFrame({"close_t": close_t, "side": side, "mid": mid.values}, index=b.index)
    sig = sig[in_win & night_ok & (side != 0) & mid.notna().values]
    ts, P = px.index, px.values
    out, free = [], pd.Timestamp.min
    for r in sig.itertuples():
        if r.close_t < free:
            continue
        i = ts.searchsorted(r.close_t + pd.Timedelta(minutes=delay - 1))
        if i >= len(ts):
            break
        t_in, entry = ts[i], P[i]
        flat_t = t_in.normalize() + pd.Timedelta(flat + ":00")
        if flat_t <= t_in:
            flat_t += pd.Timedelta("1D")
        if (flat_t - t_in) > pd.Timedelta("10h") or r.side * (r.mid - entry) <= 0:
            continue                                  # already through the target
        stop = entry - r.side * stop_mult * abs(r.mid - entry)
        j = i + 1
        why = None
        while j < len(ts):
            if ts[j] >= flat_t:
                why = "time"; break
            if r.side * (P[j] - stop) <= 0:
                why = "stop"; break
            if r.side * (P[j] - r.mid) >= 0:
                why = "target"; break
            j += 1
        if why is None:
            break
        gross = r.side * (P[j] - entry) / entry * 1e4
        out.append(dict(t_in=t_in, t_out=ts[j], side=r.side, entry=entry, exit=P[j], why=why,
                        target=r.mid, stop=stop, gross_bp=gross, net_bp=gross - cost_bp))
        free = ts[j]
    return pd.DataFrame(out)


def load(period):
    legs = {s: mr.load_nq(period, s) for s in {"E6", "B6", "A6", "N6", "E1"}}
    return {c: cross(legs[a], legs[b]) for c, (a, b, _) in CROSSES.items()}


def run(px, **kw):
    out = []
    for c, p in px.items():
        t = simulate(p, cost_bp=CROSSES[c][2], **kw)
        out.append(t.assign(cross=c))
    return pd.concat(out, ignore_index=True)


def summary(t, label):
    wk = t.t_in.dt.to_period("W").astype(str)
    m, se = mr.clustered(t.net_bp, wk)
    print(f"{label:<30} n={len(t):>5}  win={np.mean(t.net_bp > 0):5.1%}  gross={t.gross_bp.mean():+6.2f}  "
          f"net={m:+6.2f} ± {se:4.2f} bp (t {m / se:+5.2f})")
    return m, se


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "dev"
    px = load(period)
    t = run(px)
    t.to_parquet(f"cache/fx_night_{period}.parquet")
    summary(t, "A. night scalper, BB(20,2)")
    for c, g in t.groupby("cross"):
        summary(g, f"   {c}")
    print(t.why.value_counts().to_string())
    print("--- sensitivity (no verdict) ---")
    summary(run(px, delay=3), "entry 3 min later (stale check)")
    summary(run(px, n=10), "BB(10,2)")
    summary(run(px, n=40), "BB(40,2)")
    print("by year:", t.groupby(t.t_in.dt.year).net_bp.mean().round(2).to_dict())
