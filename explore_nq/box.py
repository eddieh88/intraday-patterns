"""The "Lunch Box" (Slop Box) scalp on NQ, after @MrMilkTrading's post and tips.
Rules are frozen in prereg/nq_lunch_box.md.

  box      : NQ's 12:00-12:30 New York range. Trade the day only if its height h is
             <= 15 bp of price (his "30-40 point range" at 2026 prices) and >= 10 points
  entries  : 12:30-15:00. Buy limit at low + 0.1h, sell-short limit at high - 0.1h;
             each fills only if price trades 1 tick through. One position at a time.
             After an exit, price must trade through the box middle before the next entry.
  target   : 0.5h from the entry (his "20 point scalps")
  exit     : "don't wait for your SL": a 1-minute close outside the box exits at the
             next open. A hard stop 0.25h beyond the box edge. Flat at 15:00
  box dies : at the first 1-minute close outside it (no new entries that day)
  B (tip 1): trade only with the daily trend (prior 16:00 close vs its 20-day average)
  C (tip 3): ES's own 12:00-12:30 box. A 1-minute ES close outside it also exits and
             kills the NQ box
  costs    : 1 tick slippage on stops and market exits, 0.225 points commission

Within a minute the losing order is taken: the hard stop before the target, and
no target in the minute of the fill.

  python3 explore_nq/box.py [holdout]
"""
import sys
import numpy as np
import pandas as pd
from paths import add_to_path
add_to_path("explore_nq")
import mr

TICK, COMMISSION = mr.TICK, mr.COMMISSION
MAX_BP, MIN_PTS = 15.0, 10.0
ENTRY, TARGET, STOP = 0.1, 0.5, 0.25


def box_of(m):
    b = m[(m.index.time >= pd.Timestamp("12:00").time()) & (m.index.time < pd.Timestamp("12:30").time())]
    if len(b) < 25:
        return None
    return b.high.max(), b.low.min(), b.close.iloc[-1]


def day_trades(day, nq, es=None, bias=0):
    """nq, es: that day's 1-minute bars. bias: +1 longs only, -1 shorts only, 0 both."""
    bx = box_of(nq)
    if bx is None:
        return []
    hi, lo, px = bx
    h = hi - lo
    if h > MAX_BP * 1e-4 * px or h < MIN_PTS:
        return []
    ebx = box_of(es) if es is not None else None
    t0, t1 = day + pd.Timedelta("12:30:00"), day + pd.Timedelta("15:00:00")
    mm = nq[(nq.index >= t0) & (nq.index <= t1)]
    ts, O, H, L, C = mm.index, mm.open.values, mm.high.values, mm.low.values, mm.close.values
    esc = es.close.reindex(ts).values if ebx is not None else None
    mid = (hi + lo) / 2
    lim = {1: lo + ENTRY * h, -1: hi - ENTRY * h}
    out, pos, armed, alive = [], None, True, True
    for j in range(len(ts)):
        if ts[j] >= t1:
            if pos:
                out.append({**pos, "exit_t": ts[j], "why": "15:00", "exit": O[j] - pos["side"] * TICK})
            break
        if pos is None:
            if not alive:
                break
            if not armed:
                armed = L[j] <= mid <= H[j]
                continue
            hit = [s for s in (1, -1) if bias in (0, s) and s * (lim[s] - s * TICK) >= s * (L[j] if s == 1 else H[j])]
            if len(hit) != 1:
                hit = []
            if hit:
                s = hit[0]
                pos = dict(day=day, side=s, entry=lim[s], fill_t=ts[j], h=h,
                           target=lim[s] + s * TARGET * h, stop=(lo if s == 1 else hi) - s * STOP * h)
                j_fill = j
        if pos:
            s = pos["side"]
            if s * ((L[j] if s == 1 else H[j]) - pos["stop"]) <= 0:
                out.append({**pos, "exit_t": ts[j], "why": "stop", "exit": pos["stop"] - s * TICK})
                pos, armed = None, False
            elif j > j_fill and s * ((H[j] if s == 1 else L[j]) - (pos["target"] + s * TICK)) >= 0:
                out.append({**pos, "exit_t": ts[j], "why": "target", "exit": pos["target"]})
                pos, armed = None, False
        broke = not (lo <= C[j] <= hi)
        es_broke = esc is not None and not np.isnan(esc[j]) and not (ebx[1] <= esc[j] <= ebx[0])
        if broke or es_broke:
            alive = False
            if pos and j + 1 < len(ts):
                s = pos["side"]
                out.append({**pos, "exit_t": ts[j + 1], "why": "ES break" if es_broke and not broke else "box break",
                            "exit": O[j + 1] - s * TICK})
                pos = None
    rows = pd.DataFrame(out)
    if len(rows):
        rows["pts"] = rows.side * (rows.exit - rows.entry)
        rows["pts_net"] = rows.pts - COMMISSION
    return [rows] if len(rows) else []


def run(nq, es=None, use_bias=False):
    rth = nq.between_time("09:30", "15:59")
    close = rth.groupby(rth.index.normalize()).close.last()
    trend = np.sign(close - close.rolling(20).mean()).shift()
    by_es = {d: g for d, g in es.groupby(es.index.normalize())} if es is not None else {}
    out = []
    for day, g in nq.groupby(nq.index.normalize()):
        b = int(trend.get(day, 0) or 0) if use_bias else 0
        if use_bias and b == 0:
            continue
        if es is not None and day not in by_es:
            continue
        out += day_trades(day, g, by_es.get(day), b)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def summary(tr, n_days, label):
    wk = tr.day.dt.to_period("W").astype(str)
    m, se = mr.clustered(tr.pts_net, wk)
    mh, _ = mr.clustered(tr.pts_net / tr.h, wk)
    print(f"{label:<28} days={tr.day.nunique():>4}/{n_days}  n={len(tr):>4}  win={np.mean(tr.pts_net > 0):5.1%}  "
          f"gross={tr.pts.mean():+6.2f}  net={m:+6.2f} ± {se:4.2f} pts (t {m / se:+5.2f})  net/h={mh:+.3f}")


if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "dev"
    nq, es = mr.load_nq(period), mr.load_nq(period, "ES")
    n_days = nq.index.normalize().nunique()
    res = {"A": run(nq), "B": run(nq, use_bias=True), "C": run(nq, es)}
    for k, lab in (("A", "A. box fade, both sides"), ("B", "B. + daily-trend bias"), ("C", "C. + ES box exit")):
        res[k].to_parquet(f"cache/nq_box_{k}_{period}.parquet")
        summary(res[k], n_days, lab)
    a = res["A"]
    print(a.why.value_counts().to_string())
    print(a.groupby("side").pts_net.agg(["count", "mean"]).round(2).to_string())
