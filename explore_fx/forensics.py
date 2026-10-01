"""Pixel forensics of the posted MT5 chart (explore_fx/figures/their_curve_hires.png,
3582 x 1084). The x-axis counts deals, not time.

Calibration, read off the image's own gridlines:
  balance panel : gridlines every 60.5 px, $113,965 at row 32 ... $98,990 at row 818.5
                  -> $19.04 per px; the line is ~3 px thick
  margin panel  : 0% at row 1018, 10% at row 826 (192 px per 10%)
  dates         : labels on every other vertical gridline, from x = 3, ~120.9 px apart

Extracted:
  balance steps : the line's level per column (continuity-tracked), then runs of same-sign
                  change of at least 2 px (~$38) = one step. Smaller moves hide in the
                  line's width.
  margin        : bar height per column; an episode = a run of columns with load > 0;
                  its peak height; the quantum of the peak heights
  per episode   : the balance steps inside its x-range

  python3 explore_fx/forensics.py -> explore_fx/forensics_steps.csv, forensics_episodes.csv
"""
import numpy as np
import pandas as pd
from PIL import Image

IMG = "explore_fx/figures/their_curve_hires.png"
Y_TOP, Y_BOT, V_TOP, V_BOT = 32.0, 818.5, 113965.0, 98990.0
PXD = (V_TOP - V_BOT) / (Y_BOT - Y_TOP)
M0, M10 = 1018, 826
X_END = 3453


def load():
    im = np.array(Image.open(IMG).convert("RGB")).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    navy = (b > 90) & (r < 80) & (g < 100) & (b - r > 45)
    green = (g > 140) & (r < 160) & (b < 120) & (g - r > 40)
    return navy, green


def balance(navy):
    top = np.array([np.nonzero(navy[25:822, x])[0].min() + 25 if navy[25:822, x].any() else np.nan for x in range(X_END)])
    bot = np.array([np.nonzero(navy[25:822, x])[0].max() + 25 if navy[25:822, x].any() else np.nan for x in range(X_END)])
    thick = np.nanmedian(bot - top)
    # level = the line's centre, tracked: a column taller than the line width holds a vertical
    # segment, entered at the end nearest the previous level and left at the other end
    lvl = np.full(X_END, np.nan)
    prev = (top[0] + bot[0]) / 2
    for x in range(X_END):
        if np.isnan(top[x]):
            lvl[x] = prev
            continue
        if bot[x] - top[x] > thick + 1:
            lo, hi = top[x] + thick / 2, bot[x] - thick / 2
            prev = hi if abs(lo - prev) < abs(hi - prev) else lo
        else:
            prev = (top[x] + bot[x]) / 2
        lvl[x] = prev
    return V_TOP - (lvl - Y_TOP) * PXD, thick


def steps(bal, min_px=2.0):
    d = np.diff(bal)
    out, i = [], 0
    while i < len(d):
        if abs(d[i]) > 0.5 * PXD:
            j, s = i, np.sign(d[i])
            while j < len(d) and abs(d[j]) > 0.5 * PXD and np.sign(d[j]) == s:
                j += 1
            size = d[i:j].sum()
            if abs(size) >= min_px * PXD:
                out.append((i, j, size))
            i = j
        else:
            i += 1
    return pd.DataFrame(out, columns=["x0", "x1", "usd"])


def margin(green):
    h = np.array([(M0 - (np.nonzero(green[828:M0 + 2, x])[0].min() + 828)) if green[828:M0 + 2, x].any() else 0
                  for x in range(X_END)], float)
    load = h / (M0 - M10) * 10
    ep, x = [], 0
    while x < X_END:
        if load[x] > 0.15:
            j = x
            while j < X_END and load[j] > 0.15:
                j += 1
            ep.append((x, j, load[x:j].max()))
            x = j
        else:
            x += 1
    return load, pd.DataFrame(ep, columns=["x0", "x1", "peak_pct"])


if __name__ == "__main__":
    navy, green = load()
    bal, thick = balance(navy)
    st = steps(bal)
    up, dn = st[st.usd > 0], st[st.usd < 0]
    print(f"line thickness {thick:.0f} px (~${thick * PXD:.0f}); balance ${bal[0]:,.0f} -> ${bal[-1]:,.0f}")
    print(f"steps >= ~$38: {len(st)}  up {len(up)} ({len(up)/len(st):.0%})  down {len(dn)}")
    bins = np.arange(0, 400, 19.04 * 1)
    print("bin edges $:", bins[::2].round(0).astype(int).tolist())
    print("down |$| hist (1px bins):", np.histogram(-dn.usd, bins)[0].tolist())
    print("up   $   hist (1px bins):", np.histogram(up.usd, bins)[0].tolist())
    print("down quantiles 10/25/50/75/90:", np.percentile(-dn.usd, [10, 25, 50, 75, 90]).round(0),
          " up quantiles:", np.percentile(up.usd, [10, 25, 50, 75, 90]).round(0))
    load, ep = margin(green)
    print(f"\nmargin episodes: {len(ep)}; peak load quantiles:", np.percentile(ep.peak_pct, [10, 25, 50, 75, 90]).round(2))
    hp = np.histogram(ep.peak_pct, bins=np.arange(0, 5, 0.1))
    print("peak % histogram (0.1 bins, nonzero):", {round(a, 1): int(c) for a, c in zip(hp[1][:-1], hp[0]) if c})
    ep["steps"] = [((st.x0 >= a - 2) & (st.x0 <= b + 2)).sum() for a, b in zip(ep.x0, ep.x1)]
    print("balance steps per episode:", ep.steps.value_counts().sort_index().to_dict(),
          f" mean {ep.steps.mean():.2f};  steps outside any episode: {len(st) - ep.steps.sum()}")
    st.to_csv("explore_fx/forensics_steps.csv", index=False, float_format="%.1f")
    ep.to_csv("explore_fx/forensics_episodes.csv", index=False, float_format="%.3f")
