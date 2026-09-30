"""EXPLORATORY. The night scalper's cumulative result under published cost levels
(prereg/fx_night_scalper.md, post-verdict cost check).

Each trade's return in bp is summed, so the y-axis is the % return on an account
that puts its full value into every trade (1x notional per trade). Costs are the
raw spread plus the IBKR commission tier. "Night x3" triples the published average
spread, as a guess at overnight spreads (we have no quote data).

  python3 explore_fx/plot_night_costs.py -> explore_fx/figures/night_costs.png
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PX = {"EURGBP": 0.86, "EURCHF": 0.95, "AUDNZD": 1.09}
SPREAD = {"EURGBP": 0.1, "EURCHF": 0.1, "AUDNZD": 0.6}
SCEN = [("Before costs", None, None, "#2a78d6"),
        ("IBKR >$5B/mo, average spread", 0.08, 1, "#eb6834"),
        ("IBKR >$5B/mo, night spread ×3", 0.08, 3, "#1baf7a"),
        ("IBKR <$1B/mo, average spread", 0.20, 1, "#eda100")]
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#1f1f1e", "#6b6a64", "#e4e3dd"
HOLD = pd.Timestamp("2025-04-01")

t = pd.concat([pd.read_parquet(f"cache/fx_night_{p}.parquet") for p in ("dev", "holdout")]).sort_values("t_out")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": MUTED})
fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), sharey=True, facecolor=SURFACE)
rows = []
for ax, (title, sub) in zip(axes, (("All three crosses", t),
                                   ("EURGBP + EURCHF only (AUDNZD dropped after seeing results)",
                                    t[t.cross != "AUDNZD"]))):
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.axvline(HOLD, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.text(HOLD, 0.98, " holdout", transform=ax.get_xaxis_transform(), color=MUTED, fontsize=9, va="top")
    ends = []
    for name, side, mult, col in SCEN:
        cost = 0 if side is None else sub.cross.map(lambda c: SPREAD[c] * mult / PX[c] + 2 * side)
        net = (sub.gross_bp - cost) / 100
        eq = net.groupby(sub.t_out.dt.normalize()).sum().cumsum()
        ax.plot(eq.index, eq.values, color=col, lw=2)
        ends.append((eq.values[-1], name, col))
        rows.append((title, name, round(eq.values[-1], 1)))
    ends.sort()
    placed = []
    for v, name, col in ends:                 # nudge labels apart
        y = v if not placed or v - placed[-1] > 4.5 else placed[-1] + 4.5
        placed.append(y)
        ax.annotate(f"{name}  {v:+.0f}%", (eq.index[-1], v), xytext=(eq.index[-1] + pd.Timedelta("25D"), y),
                    color=INK, fontsize=8.5, va="center",
                    arrowprops=dict(arrowstyle="-", color=col, lw=1))
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.set_xlim(pd.Timestamp("2021-01-01"), pd.Timestamp("2029-06-01"))
    ax.set_xticks(pd.date_range("2021-01-01", "2026-01-01", freq="YS"))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
axes[0].set_ylabel("Cumulative return, % (1× notional per trade)")
axes[0].yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
fig.text(0.06, 1.0, "Night scalper under published FX costs", fontsize=14, color=INK, weight="bold")
fig.text(0.06, 0.955, "Bollinger(20, 2) fade, 18:15–01:00 New York, flat at 02:00. Costs are raw spread + "
         "Interactive Brokers commission tier. Night ×3 is a guess; we have no quote data.",
         fontsize=9.5, color=MUTED)
fig.savefig("explore_fx/figures/night_costs.png", dpi=150, bbox_inches="tight", facecolor=SURFACE)
for r in rows:
    print(r)
