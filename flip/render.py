"""Pictures of the silent flip: the setup as taught, real detections, and the result.

  python3 flip/render.py   -> flip/figures/schematic.png, sample_real.png, result.png

The real sample is drawn at random from the development trades (primary spec),
not picked by outcome: three shorts and three longs.
"""
import glob

import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from paths import add_to_path
add_to_path("flip", "selection")
import sim
from flip_stats import clustered, clustered_diff, spec_mask, net
from run import sessions, DAY

UP, DN, INK, MUTE, GRID = "#2a9d8f", "#e76f51", "#1d2433", "#6b7280", "#eef0f3"
LEVEL, FLIP, SETUP = "#2463b0", "#7b5ea7", "#c98a12"
WIN, LOSS = "#1b7f4d", "#c0392b"
OUT = "flip/figures"


def candles(ax, O, H, L, C, x0=0, w=.62):
    for i, (o, h, l, c) in enumerate(zip(O, H, L, C)):
        col = UP if c >= o else DN
        ax.vlines(x0 + i, l, h, color=col, lw=1.1, zorder=3)
        ax.add_patch(Rectangle((x0 + i - w / 2, min(o, c)), w, max(abs(c - o), 1e-9), color=col, zorder=4))


def level_line(ax, y, name, color, x1, ls="-"):
    ax.axhline(y, color=color, lw=1.4, ls=ls, zorder=2)
    ax.text(x1, y, f" {name} {y:.2f}", color=color, fontsize=8.5, va="center", ha="left", fontweight="bold")


def tidy(ax):
    for k in ("top", "right"):
        ax.spines[k].set_visible(False)
    ax.yaxis.grid(True, color=GRID); ax.tick_params(labelsize=8.5)


# ---------- 1. the setup as taught ----------
def schematic():
    fig, axes = plt.subplots(1, 2, figsize=(16, 6.6))
    yday = [(100.2, 100.9, 99.8, 100.6), (100.6, 101.5, 100.4, 101.3), (101.3, 102.0, 101.0, 101.4),
            (101.4, 101.6, 100.7, 100.9), (100.9, 101.2, 100.2, 100.4), (100.4, 100.8, 99.6, 99.9),
            (99.9, 100.4, 99.5, 100.2), (100.2, 100.7, 100.0, 100.5)]
    today_short = [(100.6, 102.75, 100.5, 102.5), (102.5, 102.7, 101.9, 102.1),
                   (102.1, 102.2, 101.3, 101.4), (101.4, 101.5, 100.6, 100.8), (100.8, 100.9, 99.9, 100.1),
                   (100.1, 100.2, 99.4, 99.6)]
    for ax, short in zip(axes, (True, False)):
        yd = yday if short else [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in yday]
        td = today_short if short else [(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in today_short]
        O, H, L, C = (np.array(x) for x in zip(*yd))
        candles(ax, O, H, L, C)
        O2, H2, L2, C2 = (np.array(x) for x in zip(*td))
        x0 = len(yd) + 1
        candles(ax, O2, H2, L2, C2, x0)
        ax.axvline(x0 - 1, color=MUTE, lw=1, ls=":")
        ax.text(x0 - 1.2, 103.3 if short else 96.7, "09:30", ha="right", fontsize=8, color=MUTE)
        RH, RL = H.max(), L.min()
        FH, FL = (102.8, 99.0) if short else (101.0, 97.2)
        xr = x0 + len(td) + .3
        level_line(ax, RH, "range high", LEVEL, xr); level_line(ax, RL, "range low", LEVEL, xr)
        level_line(ax, FH, "flip high", FLIP, xr, "--"); level_line(ax, FL, "flip low", FLIP, xr, "--")
        for k, lab in ((0, "1  strong\nopening candle"), (1, "2  silent\ncandle")):
            ax.axvspan(x0 + k - .45, x0 + k + .45, color=SETUP, alpha=.16, zorder=0)
            y = (H2[k] + .35) if short else (L2[k] - .35)
            ax.text(x0 + k, y, lab, ha="center", va="bottom" if short else "top", fontsize=8.5, color=SETUP, fontweight="bold")
        trig = L2[1] if short else H2[1]
        stop = (max(H2[0], H2[1]) + .1) if short else (min(L2[0], L2[1]) - .1)
        tgt = RL if short else RH
        ax.hlines(trig, x0 + 1.5, x0 + len(td) - .3, color=INK, lw=1.5)
        ax.hlines(stop, x0 + 1.5, x0 + len(td) - .3, color=LOSS, lw=1.3, ls="--")
        ax.annotate("", xy=(x0 + 2.2, tgt), xytext=(x0 + 2.2, trig), arrowprops=dict(arrowstyle="->", color=WIN, lw=1.6))
        ax.text(x0 + 1.55, trig, ("sell-stop at candle 2's low" if short else "buy-stop at candle 2's high"),
                ha="right", va="center", fontsize=8.5, color=INK)
        ax.text(x0 + 1.55, stop, "stop beyond both highs" if short else "stop beyond both lows",
                ha="right", va="center", fontsize=8.5, color=LOSS)
        ax.text(x0 + 2.4, (trig + tgt) / 2, "target: the other\nside of yesterday", fontsize=8.5, color=WIN, va="center")
        ax.set_xticks([3.5, x0 + 2.5]); ax.set_xticklabels(["yesterday (15-min)", "today, first 90 minutes"], fontsize=9)
        ax.set_xlim(-1, x0 + len(td) + 3.2)
        ax.set_title(("SHORT: a strong green candle runs into the flip high" if short
                      else "LONG: a strong red candle runs into the range low"), fontsize=12, fontweight="bold",
                     color=INK, loc="left")
        tidy(ax)
    fig.suptitle("The silent flip, as taught", fontsize=16, fontweight="bold", x=.02, ha="left", y=.99)
    fig.text(.02, .925, "Drawn, not real data. Levels: yesterday's high and low, and the most recent earlier swing beyond each. "
             "Enter only if price breaks candle 2 in the first hour.", fontsize=10.5, color=MUTE)
    fig.tight_layout(rect=(0, 0, 1, .91))
    fig.savefig(f"{OUT}/schematic.png", dpi=110); plt.close(fig)


# ---------- 2. real detections ----------
def exit_bar(o, h, l, c, j, side, stop, tgt):
    for i in range(j, len(c)):
        if (side < 0 and h[i] >= stop) or (side > 0 and l[i] <= stop):
            return i
        if i > j and ((side < 0 and l[i] <= tgt) or (side > 0 and h[i] >= tgt)):
            return i
    return len(c) - 1


def sample_real():
    T = pd.read_parquet("cache/flip_dev.parquet")
    R = T[spec_mask(T, sim.PRIMARY) & (T.kind == "real")]
    pick = pd.concat([R[R.side < 0].sample(3, random_state=4), R[R.side > 0].sample(3, random_state=4)])
    files = sorted(glob.glob("cache/mp5min/*.parquet"))
    fig, axes = plt.subplots(3, 2, figsize=(19, 17))
    for ax, tr in zip(axes.T.ravel(), pick.itertuples()):
        k = files.index(next(f for f in files if DAY(f) == tr.date))
        hist = []
        for f in files[max(0, k - sim.LOOKBACK - 2):k]:
            s = sessions(f, {tr.symbol}).get(tr.symbol)
            if s is not None and len(s[3]) >= 6:
                hist.append(sim.name_day(*s, [], None)[1])
        o, h, l, c, hh = sessions(files[k], {tr.symbol})[tr.symbol]
        O, H, L, C, starts = sim.bars15(o, h, l, c, hh)
        RH, RL, FH, FL = sim.levels_from(hist)
        p = sim.pattern(O, H, L, C, tr.atr, RH, RL, FH, FL, sim.PRIMARY)
        ex = sim.execute(o, h, l, c, hh, p)
        # yesterday's and today's 15-minute candles
        prev = [f for f in files[max(0, k - 5):k] if tr.symbol in sessions(f, {tr.symbol})][-1]
        po, ph, pl, pc, phh = sessions(prev, {tr.symbol})[tr.symbol]
        PO, PH, PL, PC, _ = sim.bars15(po, ph, pl, pc, phh)
        candles(ax, PO, PH, PL, PC)
        x0 = len(PO) + 1
        candles(ax, O, H, L, C, x0)
        ax.axvline(x0 - 1, color=MUTE, lw=1, ls=":")
        xr = x0 + len(O) + .3
        for v, nm, col, ls in ((RH, "RH", LEVEL, "-"), (RL, "RL", LEVEL, "-"), (FH, "FH", FLIP, "--"), (FL, "FL", FLIP, "--")):
            if np.isfinite(v):
                level_line(ax, v, nm, col, xr, ls)
        for kk in (0, 1):
            ax.axvspan(x0 + kk - .45, x0 + kk + .45, color=SETUP, alpha=.18, zorder=0)
        side = p["side"]
        jx = exit_bar(o, h, l, c, ex["j"], side, p["stop"], p["tgt"])
        xf = x0 + np.searchsorted(starts, ex["j"], side="right") - 1
        xe = x0 + np.searchsorted(starts, jx, side="right") - 1
        ax.hlines(p["stop"], xf, x0 + len(O) - .5, color=LOSS, lw=1.3, ls="--")
        ax.hlines(p["tgt"], xf, x0 + len(O) - .5, color=WIN, lw=1.3, ls="--")
        ax.plot(xf, ex["fill"], marker="<" if side < 0 else ">", color=INK, ms=10, zorder=6)
        ax.plot(xe, (p["stop"] if ex["out"] == 0 else p["tgt"] if ex["out"] == 1 else c[-1]), marker="X",
                color="#6d2e8c", ms=11, mec="white", zorder=6)
        nr = tr.R - 3 * tr.cost
        col = WIN if nr > 0 else LOSS
        how = {0: "stopped", 1: "target", 2: "at the close"}[ex["out"]]
        ax.set_title(f"{tr.symbol.replace('-DELISTED', '')}  {tr.date:%b %d, %Y}  ·  "
                     f"{'SHORT' if side < 0 else 'LONG'} at {tr.level}  ·  entry {int(tr.fill_t)}:{round(tr.fill_t % 1 * 60):02d}",
                     fontsize=11.5, fontweight="bold", color=INK, loc="left")
        ax.text(.01, .97, f"{how}: {nr:+.2f}R net  ·  target {tr.tgt_R:.1f}R away  ·  1R = {tr.risk / tr.fill:.2%}",
                transform=ax.transAxes, fontsize=9.5, fontweight="bold", va="top", color=col,
                bbox=dict(boxstyle="round,pad=.3", fc="white", ec=col))
        lo = np.nanmin([PL.min(), L.min(), p["stop"], p["tgt"]]); hi = np.nanmax([PH.max(), H.max(), p["stop"], p["tgt"]])
        lv = [v for v in (FH, FL) if np.isfinite(v) and lo - (hi - lo) * .6 < v < hi + (hi - lo) * .6]
        lo, hi = min([lo] + lv), max([hi] + lv)
        ax.set_ylim(lo - (hi - lo) * .05, hi + (hi - lo) * .16)
        ax.set_xticks([len(PO) / 2, x0 + len(O) / 2]); ax.set_xticklabels(["yesterday", "trade day"], fontsize=9)
        ax.set_xlim(-1, x0 + len(O) + 5)
        tidy(ax)
    fig.suptitle("The silent flip in the data: a random sample, not picked by outcome", fontsize=16,
                 fontweight="bold", x=.02, ha="left", y=.995)
    fig.text(.02, .968, "Development trades, primary rules, 15-minute candles. Shaded: candles 1 and 2. Solid blue: yesterday's high/low. "
             "Dashed purple: flip levels. Triangle: entry. X: exit.", fontsize=10.5, color=MUTE)
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(f"{OUT}/sample_real.png", dpi=100); plt.close(fig)


# ---------- 3. the result ----------
def result():
    T = pd.read_parquet("cache/flip_dev.parquet")
    P = T[spec_mask(T, sim.PRIMARY)]
    real, fake = P[P.kind == "real"], P[P.kind == "fake"]
    rows = [("Real levels (877 trades)", *clustered(net(real), real.date)[:2]),
            ("Fake levels from another day (915)", *clustered(net(fake), fake.date)[:2]),
            ("Random entry, same trades (877)", *clustered(net(real, "R_rand", "c_rand"), real.date)[:2])]
    for lv in ("RH", "FH", "RL", "FL"):
        x = real[real.level == lv]
        rows.append((f"  real, at {lv} ({len(x)})", *clustered(net(x), x.date)[:2]))
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ys = np.arange(len(rows))[::-1]
    for y, (lab, m, se) in zip(ys, rows):
        sub = lab.startswith("  ")
        ax.hlines(y, m - 1.96 * se, m + 1.96 * se, color="#9aa3ad", lw=2.2, zorder=2)
        ax.plot(m, y, "o", color=INK if not sub else MUTE, ms=9 if not sub else 7, mec="white", mew=2, zorder=3)
        ax.text(m, y + .28, f"{m:+.3f}R", ha="center", fontsize=8.5, color=INK)
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=10)
    ax.set_xlabel("net R per trade after a 3 bp cost (dot = mean, bar = 95% interval)", fontsize=9.5, color=MUTE)
    ax.set_title("The silent flip loses, and fake levels do just as well", fontsize=13, fontweight="bold",
                 color=INK, loc="left")
    for k in ("top", "right", "left"):
        ax.spines[k].set_visible(False)
    ax.xaxis.grid(True, color=GRID); ax.tick_params(axis="y", length=0)
    fig.text(.01, .01, "Development 2021-01 to 2025-03, top 100 US stocks a day. +1R = winning what you risked.",
             fontsize=8.5, color=MUTE)
    fig.tight_layout(rect=(0, .03, 1, 1))
    fig.savefig(f"{OUT}/result.png", dpi=120); plt.close(fig)


if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    schematic(); result(); sample_real()
    print("wrote", ", ".join(f"{OUT}/{n}" for n in ("schematic.png", "result.png", "sample_real.png")))
