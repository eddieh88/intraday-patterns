"""Random, outcome-blind sample of structure + zone trades on futures, 30-minute bars.

  python3 explore_fut/render.py   -> explore_fut/figures/sample_zones.png
"""
import pandas as pd, numpy as np, sys
from paths import add_to_path
add_to_path("explore_fut")
import structure as S
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
UP, DN, INK, MUTE = "#2a9d8f", "#e76f51", "#1d2433", "#6b7280"
NAME = {"GC": "Gold (GC)", "E6": "Euro (E6)", "B6": "Pound (B6)", "A6": "Aussie dollar (A6)", "J1": "Yen (J1)"}
T = pd.read_parquet("cache/fut_zone_trades.parquet"); F = T[T.filled]
pick = pd.concat([F[F.side == 1].sample(2, random_state=11), F[F.side == -1].sample(2, random_state=11)]).sort_values("bos")
data = S.load()
fig = plt.figure(figsize=(19, 14.5)); G = fig.add_gridspec(2, 2, wspace=.2, hspace=.22, top=.9, bottom=.05, left=.05, right=.9)
for n, ev in enumerate(pick.itertuples()):
    m30 = S.bars(data[ev.sym], "30min")
    start = min(ev.origin, ev.zone_t) - pd.Timedelta("10h"); end = ev.exit_t + pd.Timedelta("6h")
    w = m30.loc[start:end]
    if len(w) > 220: w = m30.loc[start:ev.exit_t + pd.Timedelta("3h")].iloc[:220]
    X = lambda t: int(np.searchsorted(w.index, t, side="right")) - 1
    ax = fig.add_subplot(G[n // 2, n % 2])
    for i, (t_, b) in enumerate(w.iterrows()):
        c = UP if b.close >= b.open else DN
        ax.vlines(i, b.low, b.high, color=c, lw=1, zorder=2)
        ax.add_patch(Rectangle((i - .35, min(b.open, b.close)), .7, max(abs(b.close - b.open), 1e-9), facecolor=c, edgecolor=c, zorder=3))
    side = ev.side; win = ev.R > 0
    ax.axvspan(X(ev.fill_t) - .5, X(ev.exit_t) + .5, color="#e7f5ee" if win else "#fbe9e4", zorder=0)
    zx0, zx1 = X(ev.zone_t), X(ev.fill_t)
    lo_, hi_ = sorted([ev.near, ev.far])
    ax.add_patch(Rectangle((zx0 - .5, lo_), max(zx1 - zx0, 1) + .5, hi_ - lo_, facecolor="#ececec", alpha=.9, edgecolor="#333", lw=1, zorder=1))
    ax.text(zx0, lo_ if side > 0 else hi_, " demand" if side > 0 else " supply", fontsize=8.5, color="#333",
            va="top" if side > 0 else "bottom", fontweight="bold")
    bx = X(ev.bos)
    ax.hlines(ev.level, max(0, bx - 25), bx + 2, color="#b8860b", lw=1.3, ls="--", zorder=4)
    ax.text(max(0, bx - 25), ev.level, "BoS (1h close) ", fontsize=8.5, color="#9a7b20", va="bottom", fontweight="bold")
    ext_x = X(ev.zone_t) + 1
    ax.plot(ext_x, ev.far, "o", ms=16, mfc="none", mec="#d62828", mew=1.6, zorder=6)
    ax.annotate(("swept low" if ev.swept else "swing low") if side > 0 else ("swept high" if ev.swept else "swing high"),
                (ext_x, ev.far), xytext=(0, -26 if side > 0 else 18), textcoords="offset points", ha="center", fontsize=8, color="#d62828")
    fx, xx = X(ev.fill_t), X(ev.exit_t)
    span = max(xx - fx, 6) + 1
    ax.add_patch(Rectangle((fx - .5, min(ev.entry, ev.target)), span, abs(ev.target - ev.entry), facecolor="#9dc3f0", alpha=.45, lw=0, zorder=1))
    ax.add_patch(Rectangle((fx - .5, min(ev.entry, ev.stop)), span, abs(ev.stop - ev.entry), facecolor="#b0b0b0", alpha=.55, lw=0, zorder=1))
    for y, col, lab in ((ev.target, "#1f5fa8", f"target {ev.target:.5g}"), (ev.entry, INK, f"entry {ev.entry:.5g}"),
                        (ev.stop, "#555", f"stop {ev.stop:.5g}")):
        ax.text(fx + span, y, " " + lab, fontsize=8.5, color=col, va="center", fontweight="bold")
    ax.plot(fx, ev.entry, marker=">" if side > 0 else "<", color=INK, ms=9, zorder=6)
    ax.plot(xx, ev.stop if ev.how == "stop" else (ev.target if ev.how == "target" else w.close.iloc[min(xx, len(w)-1)]),
            marker="X", color="#6d2e8c", ms=11, zorder=7, mec="white")
    col = "#1b7f4d" if win else "#c0392b"
    ax.text(.015, .97, f"{NAME[ev.sym]} — {'LONG' if side > 0 else 'SHORT'} — break {ev.bos:%b %d, %Y %H:%M}", transform=ax.transAxes,
            fontsize=12.5, fontweight="bold", va="top", color=INK)
    ax.text(.015, .9, f"{ev.how}: {ev.R:+.1f}R  ·  planned {ev.rr:.1f}:1  ·  1R = {ev.R_ticks:.0f} ticks  ·  "
            f"{'discount' if (ev.cheap and side > 0) else ('premium' if (ev.cheap and side < 0) else 'mid-range')}", transform=ax.transAxes,
            fontsize=10.5, fontweight="bold", va="top", color=col, bbox=dict(boxstyle="round,pad=.35", fc="white", ec=col))
    ticks = list(range(0, len(w), max(1, len(w) // 6)))
    ax.set_xticks(ticks); ax.set_xticklabels([w.index[i].strftime("%b %d\n%H:%M") for i in ticks], fontsize=8)
    ax.set_xlim(-1, len(w) + 12); ax.yaxis.grid(True, color="#eef0f3"); ax.tick_params(axis="y", labelsize=8)
    for k in ("top", "right"): ax.spines[k].set_visible(False)
    ymin = min(w.low.min(), ev.stop, ev.target); ymax = max(w.high.max(), ev.stop, ev.target); pad = (ymax - ymin) * .07
    ax.set_ylim(ymin - pad * 1.5, ymax + pad * 3)
fig.suptitle("Market structure + supply/demand zones on futures — random sample, not picked by outcome", fontsize=16.5,
             fontweight="bold", x=.05, ha="left", y=.985)
fig.text(.05, .935, f"{len(F):,} filled trades, 2021–Mar 2025, gold and 4 currency futures, 30-minute bars, structure on the 1-hour. Zone = the base of the impulse; "
         "entry at its near edge; stop beyond the swing extreme; target the impulse extreme.\nBlue = reward, grey = risk.", fontsize=10.5, ha="left", color=MUTE)
fig.savefig("explore_fut/figures/sample_zones.png", dpi=110); print("explore_fut/figures/sample_zones.png")
