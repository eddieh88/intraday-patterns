# One-rule FX mean reversion

What could be behind an X post: "best mean reversion strategy I've ever built.
Multi-asset (FX), one timeframe, same parameters/management, one specific
parameter… literally just one rule". It came with an MT5 equity curve from 2018 to 2026.

**What the curve shows:**
- About +1.4% a year, with a max drawdown of about 1.6%.
- Floating losses on open positions, which is typical of mean reversion.
- The x-axis counts trades, not time. Trades bunch in volatile stretches (2022,
  early 2023, 2025–26) and nearly stop in calm 2021.

**What `one_rule.py` found** (63 variants, six CME currency futures, 2021-01 to
2025-03, `one_rule_dev.csv`):
- Every rule scaled to volatility trades as often in 2022 as in 2021. That covers
  RSI, Bollinger, N-bar extremes, IBS and ATR-scaled big bars. None of them matches
  the curve's timing.
- Only **fixed-threshold** rules do, trading 3–30× more in 2022.
- The best variant overall is one of those: on 4-hour bars, fade a close more than
  1% from the 20-bar SMA, and exit back at the SMA. That makes "one specific
  parameter" the 1%.
- Hourly rules all lose to costs.

**Holdout** (`../prereg/fx_distance_fade.md`): +0.24 ATR per trade, t 0.7, 68%
winners. Same direction as development, but not confirmed.

This finds a rule that is *consistent with* his curve, not his rule.

## Against their curve (`plot_vs_theirs.py` → `figures/vs_theirs.png`)

Their balance and margin use were digitised from the screenshot
(`figures/their_curve_digitised.csv`), with dates interpolated between their
axis labels. Ours is scaled to their monthly volatility and starts at their
January 2021 balance.
- **The resemblance is only that both rise.** Quarter by quarter, the changes are
  uncorrelated: −0.00 over 16 quarters (2021 to 2025 Q1), and −0.32 over the 6
  holdout quarters.
- **Since the holdout began, the two diverge.** They rise in 2026, while ours
  gives some back.
- **Their margin use suggests at most three positions at once.** It never tops
  about 4.4%, and it steps at about 1.5%, 2.6% and 4.3%. We hold up to 6.
- Their x-axis counts trades, so stretches with no trades are squeezed out. Time
  spent in the market can't be compared.
