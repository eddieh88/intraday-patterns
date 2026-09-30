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

## Night scalper (`night.py`, pre-registered in `../prereg/fx_night_scalper.md`)

His later clues fit the classic night scalper:
- three pairs
- indicator-based
- stops, and flat by the end of the day
- spread filters

We tested a Bollinger(20, 2) fade on EURGBP, AUDNZD and EURCHF, built from futures
legs, from 18:15 to 01:00 New York and flat at 02:00. It **fails** on both periods:
−1.6 and −1.9 bp per trade net. The reversion before costs is real but tiny, +0.3
to +0.6 bp. It would pay only at costs under about half a pip, which fits "your
edge is infra". We can't test his spread filter without quote data.

### Under published costs (`plot_night_costs.py` → `figures/night_costs.png`, exploratory)

Cumulative return, with 1× notional per trade:

| | before costs | IBKR >$5B/mo, average spread | IBKR >$5B/mo, night spread ×3 | IBKR <$1B/mo, average spread |
|---|---|---|---|---|
| all three crosses | +63% | +12% | −50% | −16% |
| EURGBP + EURCHF | +54% | +33% | +16% | +15% |

- With AUDNZD included, only the most favourable cost case stays positive, and it
  has fallen since early 2026.
- The two tight crosses stay positive in every cost case. But AUDNZD was dropped
  after seeing the results.
- The September 2022 sterling crisis contributes 4.3 of the 54 points before costs,
  so it doesn't carry the result.
- The "night ×3" spread is a guess. We have no quote data.

## Is either candidate his strategy? (`match.py`, exploratory)

We checked candidates against two fingerprints of his chart:
- **Timing:** the correlation of trade rate with his, across his date-label
  intervals. Each interval holds the same number of his trades.
- **P&L:** the correlation of quarterly P&L with his.

| candidate | timing | quarterly P&L |
|---|---|---|
| night scalper (Bollinger, three crosses) | −0.47 | +0.10 |
| 1% distance fade, 4-hour | +0.38 | −0.09 |

**Neither is his.** The Bollinger scalper trades most in calm stretches, the
opposite of him. The 4-hour fade has the right timing but holds positions for days.

We then searched 105 intraday rules with a fixed threshold, a stop and flat by
16:45 New York. They cover three families (distance from the day's open, distance
from the hourly SMA, a big hourly move), six thresholds and six pre-chosen sets of
three pairs.
- **Best match:** fading an hourly move of more than 0.4% on EUR, AUD and NZD
  against USD. Timing +0.37, P&L +0.54, +1.7 bp per trade gross.
- **That is no better than chance.** When his intervals and quarters are shuffled,
  the best of the 105 scores 0.92 at the 95th percentile, against 0.91 for the real
  match.

The fixed-threshold intraday fade stays the family that fits his clues, but his
chart doesn't carry enough information to single out a rule. Identifying it needs
more from him: his trade count, win rate, average hold, or which three pairs.
