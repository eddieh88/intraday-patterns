"""EXPLORATORY. The best-matching rule from match2.py (fade the weekend gap on EUR, AUD
and NZD vs USD: gap > 0.05%, stop 0.4%, target 0.8%, flat Monday 16:45 New York)
against the digitised MT5 curve. It is scaled to their monthly volatility and starts
at their January 2021 balance, as in plot_vs_theirs.py.

  HOLDOUT_UNLOCK=final-evaluation python3 explore_fx/plot_gap_vs_theirs.py
      -> explore_fx/figures/gap_vs_theirs.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from paths import add_to_path
add_to_path("explore_fx")
import match2

SYMS, X, S, RR = ("E6", "A6", "N6"), 0.05, 0.4, 2.0
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#1f1f1e", "#6b6a64", "#e4e3dd"
THEIRS, OURS = "#2a78d6", "#eb6834"

match2.BARS.update(match2.load5())
t = pd.concat([match2.job((s, "gap", X, S, RR))[1].assign(sym=s) for s in SYMS]).sort_values("t_out")
th = pd.read_csv("explore_fx/figures/their_curve_digitised.csv", parse_dates=["date"]).set_index("date").balance
daily = t.groupby(t.t_out.dt.normalize()).net.sum()
his_m = th[th.index >= "2021-01-01"].resample("ME").last().diff()
k = his_m.std() / daily.resample("ME").sum().std()
start = th[th.index >= t.t_in.min()].iloc[0]
eq = start + k * daily.cumsum()

yr = pd.DataFrame({"theirs $": th.resample("YE").last().diff(), "gap rule $ (scaled)": (k * daily).resample("YE").sum()})
yr.index = yr.index.year
print(yr.loc[2021:].round(0).to_string())
print(f"yearly correlation 2021-2026: {yr.loc[2021:].corr().iloc[0, 1]:+.2f}")
m = his_m.dropna()
print(f"their monthly Sharpe-like ratio (2021+, digitised, time-warped): {m.mean() / m.std() * np.sqrt(12):.2f}")
print(f"gap rule: trades {len(t)}, win {np.mean(t.net > 0):.0%}, avg win {t.net[t.net > 0].mean():.1f} bp, "
      f"avg loss {t.net[t.net <= 0].mean():.1f} bp")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": MUTED})
fig, ax = plt.subplots(figsize=(13, 5.6), facecolor=SURFACE)
ax.set_facecolor(SURFACE)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.tick_params(length=0)
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)
ax.plot(th.index, th.values, color=THEIRS, lw=2)
ax.plot(eq.index, eq.values, color=OURS, lw=2, drawstyle="steps-post")
ax.axvline(pd.Timestamp("2025-04-01"), color=MUTED, lw=1, ls=(0, (3, 3)))
ax.text(th.index[-1] + pd.Timedelta("20D"), th.iloc[-1], "Theirs", color=INK, va="center")
ax.text(eq.index[-1] + pd.Timedelta("20D"), eq.iloc[-1], "Weekend-gap fade", color=INK, va="center")
ax.set_xlim(pd.Timestamp("2017-11-01"), pd.Timestamp("2027-06-01"))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.set_ylabel("Balance ($)")
ax.legend(handles=[plt.Line2D([], [], color=THEIRS, lw=2, label="Theirs (digitised MT5 backtest)"),
                   plt.Line2D([], [], color=OURS, lw=2, label="Fade the weekend gap: EUR, AUD, NZD vs USD; stop 0.4%, target 0.8%")],
          loc="upper left", frameon=False, fontsize=9, labelcolor=INK)
fig.text(0.07, 0.97, "The best-matching rule against the posted curve", fontsize=14, color=INK, weight="bold")
fig.text(0.07, 0.925, f"Scaled ×{k:.0f} $/bp to their monthly volatility, starting at their January 2021 balance. "
         "Dashed line: our holdout start. Exploratory; chosen from 312 rules.", fontsize=9.5, color=MUTED)
fig.savefig("explore_fx/figures/gap_vs_theirs.png", dpi=150, bbox_inches="tight", facecolor=SURFACE)
