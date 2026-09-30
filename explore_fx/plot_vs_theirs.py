"""Our 1% distance fade against the X post's MT5 curve, digitised from its screenshot
(explore_fx/figures/their_curve.png).

Their chart's x-axis counts trades, not time. Each date label sits on every other
vertical gridline, so dates are interpolated linearly between labels. Their balance is
the navy line; their "Deposit Load" (margin used) is the green bars. Our curve is
realised P&L per closed trade in ATR units. It is scaled so its monthly volatility
matches theirs over 2021-01 to 2026-09, and it starts from their balance in January
2021, so the slopes compare directly.

  python3 explore_fx/plot_vs_theirs.py -> explore_fx/figures/vs_theirs.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

IMG = "explore_fx/figures/their_curve.png"
LABELS = ["2018.01.15", "2018.03.07", "2018.07.09", "2018.10.15", "2019.02.07", "2019.07.01", "2019.10.31",
          "2020.01.20", "2020.04.17", "2020.12.14", "2021.05.11", "2022.02.28", "2022.05.05", "2022.07.22",
          "2022.09.30", "2023.02.02", "2023.03.20", "2023.08.02", "2024.01.24", "2024.06.04", "2024.09.13",
          "2024.12.19", "2025.02.20", "2025.04.07", "2025.08.04", "2026.02.02", "2026.04.06", "2026.05.08",
          "2026.07.13"]
X0, DX = 92 - 110, 109.96          # pixel of the first label's gridline, and label spacing
PLOT_RIGHT = 3158
Y_TOP, Y_STEP, V_TOP, V_STEP = 29.5, 55.0, 113965, 1151.92   # top panel gridlines
LOAD_0, LOAD_10 = 927, 760                                     # lower panel: 0% and 10% rows
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#1f1f1e", "#6b6a64", "#e4e3dd"
THEIRS, OURS = "#2a78d6", "#eb6834"


def pixel_dates():
    xs = X0 + DX * np.arange(len(LABELS))
    ts = pd.to_datetime(LABELS, format="%Y.%m.%d").astype("int64")
    slope = (ts[-1] - ts[-2]) / DX
    def to_date(x):
        x = np.asarray(x, float)
        out = np.interp(x, xs, ts)
        out = np.where(x > xs[-1], ts[-1] + (x - xs[-1]) * slope, out)
        return pd.to_datetime(out.astype("int64"))
    return to_date


def digitise():
    im = np.array(Image.open(IMG).convert("RGB")).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    navy = (b > 90) & (r < 70) & (g < 90) & (b - r > 50)
    green = (g > 140) & (r < 160) & (b < 120) & (g - r > 40)
    to_date = pixel_dates()
    xs = np.arange(0, PLOT_RIGHT)
    bal = np.full(len(xs), np.nan)
    load = np.zeros(len(xs))
    for i, x in enumerate(xs):
        ys = np.nonzero(navy[25:745, x])[0] + 25
        if len(ys):
            bal[i] = np.median(ys)
        gy = np.nonzero(green[752:LOAD_0, x])[0]
        if len(gy):
            load[i] = (LOAD_0 - (gy.min() + 752)) / (LOAD_0 - LOAD_10) * 10
    bal = pd.Series(bal).interpolate(limit_direction="both").values
    value = V_TOP - (bal - Y_TOP) / Y_STEP * V_STEP
    return pd.DataFrame({"date": to_date(xs), "balance": value, "load": load})


def ours(theirs):
    t = pd.read_parquet("cache/fx_dist1_trades.parquet").sort_values("t_out")
    daily = t.groupby(t.t_out.dt.normalize()).r.sum()
    th = theirs.set_index("date").balance
    th = th[th.index >= "2021-01-01"].resample("ME").last()
    ou = daily.resample("ME").sum()
    k = th.diff().std() / ou.std()
    start = theirs.loc[theirs.date >= t.t_in.min(), "balance"].iloc[0]
    eq = start + k * daily.cumsum()
    days = pd.date_range(t.t_in.min().normalize(), t.t_out.max().normalize(), freq="D")
    open_n = np.array([((t.t_in <= d + pd.Timedelta("12h")) & (t.t_out > d + pd.Timedelta("12h"))).sum()
                       for d in days])
    return eq, pd.Series(open_n, index=days), k


def main():
    th = digitise()
    eq, open_n, k = ours(th)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                         "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})
    fig, ax = plt.subplots(3, 1, figsize=(13, 8.2), sharex=True, facecolor=SURFACE,
                           gridspec_kw={"height_ratios": [3.2, 1, 1], "hspace": 0.28})
    for a in ax:
        a.set_facecolor(SURFACE)
        a.grid(axis="y", color=GRID, lw=0.8)
        a.tick_params(length=0)
        for s in ("top", "right", "left"):
            a.spines[s].set_visible(False)
    hold = pd.Timestamp("2025-04-01")

    a = ax[0]
    a.plot(th.date, th.balance, color=THEIRS, lw=2)
    a.plot(eq.index, eq.values, color=OURS, lw=2, drawstyle="steps-post")
    a.axvline(hold, color=MUTED, lw=1, ls=(0, (3, 3)))
    a.text(hold, a.get_ylim()[0] + 150, "  our holdout starts", color=MUTED, fontsize=9, va="bottom")
    a.text(th.date.iloc[-1] + pd.Timedelta("20D"), th.balance.iloc[-1], "Theirs", color=INK, va="center", fontsize=10)
    a.text(eq.index[-1] + pd.Timedelta("20D"), eq.values[-1], "Ours", color=INK, va="center", fontsize=10)
    a.set_xlim(pd.Timestamp("2017-11-01"), pd.Timestamp("2027-01-15"))
    a.set_ylabel("Balance ($)")
    a.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    a.legend(handles=[plt.Line2D([], [], color=THEIRS, lw=2, label="Theirs"),
                      plt.Line2D([], [], color=OURS, lw=2, label="Ours: 1% distance fade, 4-hour bars, 6 currency futures")],
             loc="upper left", frameon=False, fontsize=9, labelcolor=INK)
    fig.text(0.07, 0.955, "Our one-rule FX fade against the posted MT5 curve", fontsize=14, color=INK, weight="bold")
    fig.text(0.07, 0.928, f"Their balance and margin use digitised from the screenshot. Our P&L is in ATR units, scaled ×{k:,.0f} $/ATR "
             "and started at their January 2021 balance.", fontsize=9.5, color=MUTED)

    a = ax[1]
    a.fill_between(th.date, 0, th.load, color=THEIRS, lw=0, step="mid")
    a.set_ylabel("Their margin\nused (%)")
    a.set_ylim(0, max(10, th.load.max() * 1.1))

    a = ax[2]
    a.fill_between(open_n.index, 0, open_n.values, color=OURS, lw=0, step="post")
    a.axvline(hold, color=MUTED, lw=1, ls=(0, (3, 3)))
    a.set_ylabel("Our open\npositions (of 6)")
    a.set_ylim(0, 6)
    a.xaxis.set_major_locator(matplotlib.dates.YearLocator())
    a.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    both = pd.DataFrame({"theirs": th.set_index("date").balance.resample("QE").last(),
                         "ours": eq.resample("QE").last()}).dropna().diff().dropna()
    for lab, d in (("2021-2025Q1", both[both.index < hold]), ("2025Q2 on", both[both.index >= hold])):
        print(f"quarterly change correlation {lab}: {d.corr().iloc[0, 1]:+.2f} over {len(d)} quarters")
    fig.savefig("explore_fx/figures/vs_theirs.png", dpi=150, bbox_inches="tight", facecolor=SURFACE)
    th.to_csv("explore_fx/figures/their_curve_digitised.csv", index=False, float_format="%.2f")
    print(f"scale {k:.0f} $/ATR; their 2021-01 -> end: {th.balance[th.date >= '2021-01-11'].iloc[0]:.0f} -> "
          f"{th.balance.iloc[-1]:.0f}; ours ends {eq.iloc[-1]:.0f}")


if __name__ == "__main__":
    main()
