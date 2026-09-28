"""Random, outcome-blind samples of the 5-minute detections, for checking by eye.

  python3 explore5m/render.py base   -> explore5m/figures/sample_base.png
  python3 explore5m/render.py soup   -> explore5m/figures/sample_soup.png
"""
import pandas as pd, numpy as np, sys, glob
from intraday_levels import session_frames
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

UP, DN, INK, MUTE = "#2a9d8f", "#e76f51", "#1d2433", "#6b7280"
KIND = sys.argv[1] if len(sys.argv) > 1 else "base"
E = pd.read_parquet("cache/x5_events.parquet"); E = E[E.kind == KIND]
pick = pd.concat([E[E.side == 1].sample(2, random_state=4), E[E.side == -1].sample(2, random_state=4)]).sort_values("date")

fig = plt.figure(figsize=(19, 14.5)); G = fig.add_gridspec(2, 2, wspace=.2, hspace=.22, top=.9, bottom=.04, left=.04, right=.92)
for n, ev in enumerate(pick.itertuples()):
    f = glob.glob(f"cache/mp5min/*_{ev.date:%Y-%m-%d}.parquet")[0]
    g = [x for x in session_frames([f], {ev.symbol})][0][2]
    g = g[g.h >= 9.5].reset_index(drop=True).iloc[:78]
    t, side = ev.t, ev.side
    inner = G[n // 2, n % 2].subgridspec(2, 1, height_ratios=[4, 1], hspace=.03)
    ax, av = fig.add_subplot(inner[0]), fig.add_subplot(inner[1])
    r = ev.R
    ax.axvspan(t + .5, ev.exit_bar + .5, color="#e7f5ee" if r > 0 else "#fbe9e4", zorder=0)
    if KIND in ("base", "coil"):
        nb = 18 if KIND == "base" else 12
        ax.axvspan(t - nb - .5, t - .5, color="#fdf3d7", zorder=0)
        lvl = ev.level if (side > 0 or KIND == "coil") else ev.level2
        ax.hlines(lvl, t - nb, t, color="#b8860b", lw=1.2, ls="--")
        ax.text(t - nb, .02, f"{nb * 5}-min base", transform=ax.get_xaxis_transform(), fontsize=8, color="#9a7b20")
    else:
        ax.hlines(ev.level, ev.anchor, t, color="#b8860b", lw=1.2, ls="--")
        ax.plot(ev.anchor, ev.level, "o", ms=6, mfc="none", mec="#b8860b", mew=1.5)
        ax.text(ev.anchor, ev.level, f" 20-bar {'low' if side > 0 else 'high'}", fontsize=8, color="#9a7b20",
                va="top" if side > 0 else "bottom")
    ax.add_patch(Rectangle((t - .6, g.low.min()), 1.2, 1e9, color="#ffd166", alpha=.55, zorder=0))
    for i, b in g.iterrows():
        col = UP if b.close >= b.open else DN
        ax.vlines(i, b.low, b.high, color=col, lw=1.1, zorder=2)
        ax.add_patch(Rectangle((i - .36, min(b.open, b.close)), .72, max(abs(b.close - b.open), 1e-5 * b.close), facecolor=col, edgecolor=col, zorder=3))
        av.bar(i, b.volume, color="#ffb703" if i == t else ("#b8c4c2" if b.close >= b.open else "#e4c3b9"), width=.75)
    tgt = ev.entry + 3 * ev.R_pct * ev.entry * side
    x0 = ev.anchor if KIND in ("base", "coil") else t + 1
    for y, col, lab, x in ((tgt, "#1b7f4d", f"+3R  ${tgt:.2f}", t + 1), (ev.entry, INK, f"entry  ${ev.entry:.2f}", t + 1),
                           (ev.stop, "#c0392b", f"stop  ${ev.stop:.2f}", x0)):
        ax.hlines(y, x, len(g) - 1, color=col, lw=1.5, ls="-" if col == INK else "--", zorder=4)
        ax.text(len(g) + .5, y, lab, fontsize=8.5, color=col, va="center", fontweight="bold")
    if KIND in ("base", "coil"):
        ax.plot(ev.anchor, ev.stop, marker="^" if side > 0 else "v", color="#c0392b", ms=8, zorder=5)
    if KIND == "coil":
        sv = pd.read_parquet("cache/x5_slotvol.parquet", filters=[("date", "==", ev.date)])
        sv = sv[sv.symbol.astype(str) == ev.symbol].set_index("slot").slot_norm
        slots = (g.ts.dt.hour * 60 + g.ts.dt.minute).values
        av.plot(range(len(g)), [sv.get(x, np.nan) for x in slots], color="#1d2433", lw=1, ls="--")
        av.text(.01, .82, "dashed = normal volume for this time of day", transform=av.transAxes, fontsize=7.5, color=MUTE)
        ax.text(.015, .80, f"base volume {ev.base_vol:.2f}× normal  ·  breakout bar {ev.brk_volx:.1f}× normal",
                transform=ax.transAxes, fontsize=9, va="top", color=MUTE)
    ax.plot(t + 1, ev.entry, marker=">" if side > 0 else "<", color=INK, ms=9, zorder=6)
    ax.plot(ev.exit_bar, ev.exit, marker="X", color="#6d2e8c", ms=11, zorder=6, mec="white")
    col = "#1b7f4d" if r > 0 else "#c0392b"
    ax.text(.015, .97, f"{ev.symbol.replace('-DELISTED','')} — {ev.date:%b %d, %Y} — {'LONG' if side > 0 else 'SHORT'} at {ev.bar_time} close",
            transform=ax.transAxes, fontsize=12.5, fontweight="bold", va="top", color=INK)
    ax.text(.015, .885, f"{ev.how}: {r:+.1f}R  ·  1R = {ev.R_pct:.2%}", transform=ax.transAxes, fontsize=10.5, fontweight="bold",
            va="top", color=col, bbox=dict(boxstyle="round,pad=.35", fc="white", ec=col))
    ymin = min(g.low.min(), ev.stop, tgt); ymax = max(g.high.max(), ev.stop, tgt); pad = (ymax - ymin) * .07
    ax.set_ylim(ymin - pad, ymax + pad * 3.5)
    ticks = [i for i in range(0, len(g), 12)]
    av.set_xticks(ticks); av.set_xticklabels([g.ts.iloc[i].strftime("%H:%M") for i in ticks], fontsize=8)
    ax.set_xticks([]); av.set_yticks([])
    for a in (ax, av):
        a.set_xlim(-1, len(g) + 12)
        for k in ("top", "right"): a.spines[k].set_visible(False)
    ax.yaxis.grid(True, color="#eef0f3"); ax.tick_params(labelsize=8.5)
title = {"base": "5-minute tension-base breakouts", "soup": "5-minute Turtle Soup (failed break of the 20-bar channel)",
         "coil": "5-minute coil breakouts"}[KIND]
fig.suptitle(f"{title} — random sample, not picked by outcome", fontsize=17, fontweight="bold", x=.04, ha="left", y=.985)
fig.text(.04, .945, f"{len(E):,} signals on every 5th session, 2021–Mar 2025. Two longs, two shorts. Entry next bar's open; "
         f"{ {'base': 'stop beyond the latest swing low/high', 'coil': 'stop beyond the last 4 bars', 'soup': 'stop 0.25 ATR beyond the signal bar'}[KIND]}; +3R; flat at the close.",
         fontsize=11, ha="left", color=MUTE)
out = f"explore5m/figures/sample_{KIND}.png"; fig.savefig(out, dpi=110); print(out)
