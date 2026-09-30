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
