# FX: reverse-engineering a posted one-rule strategy, and our own

**Summary (closed 2026-10-01).** Read this first; the sections below are the
chronological record.
- **His strategy:** the rule was not identified; its shape was. Trades come in groups
  of pairs opened on an hourly bar in the European morning. They close at a fixed time,
  the 17:00 New York server boundary (delayed by his spread filter). The stop is about
  30 pips, there is no target, results are scratch-heavy, sizing is risk-based, the
  trades are Monday-heavy, and they run 4–5 per pair per month (about 5× that in
  volatile years). Evidence: the MT5 chart's labels, steps and margin panel
  (`forensics.py`), and Darwinex tooltips.
- **Searches:** every candidate family either matched his timing or his profits, never
  both. Matching the tooltip pips to actual July 2026 trades is at chance level.
- **Our own sibling:** the evening dollar-basket fade (`basket_match.py`). It failed
  the sealed 2010–2014 test net of costs and is gross-positive in every year
  (`../prereg/own_fx_basket.md`).
- **His book (Darwinex tooltips):** at least five clock-exit strategies across FX, a
  probable index, gold and a quiet cross, all sized to the same risk.
- **The full write-up for outside readers** is the shared document "Reverse-engineering
  a one-rule FX mean-reversion strategy".

## Initial search: one-rule FX mean reversion

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

## Second search, built on his own descriptions (`match2.py`, `plot_gap_vs_theirs.py`, exploratory)

His letters (kieranduff.com) say:
- "no negatively skewed strategies", "minimum 1:1 risk-to-reward"
- "one bullet in the chamber", fixed stops, daily closes

His worked example: "if Friday is bearish, buy the Sunday open, 1:1 with a fixed
stop". So every rule here has a fixed stop, a target ≥ 1:1, one position, and is
flat by 16:45 New York. There are 312 combinations: previous-day fade, Asian-session
fade, post-fix fade, weekend-gap fade, the Friday rule, hourly Bollinger and RSI.

- **The weekend-gap fade matches his fingerprint better than chance.** It holds
  the whole top 15, with the best at 1.20 against a shuffled 95th percentile of 0.99.
  The match is mostly timing (+0.73): a fixed gap threshold fires more in volatile
  weeks, and so does he.
- **Its P&L is not his.** The best candidate loses in 2023–2025, while his curve
  rises. Yearly correlation +0.41 over 6 years; Sharpe about 0.1, against about 1.4
  for his digitised curve.
- None of the 312 passes his own bar (Sharpe ≥ 1, 200+ trades).
- The Friday rule translated to FX doesn't rank.

What his rule probably shares with these: it fires on a fixed-size move, so it trades
more when FX is volatile. It has positive skew and is flat daily. What we can't
reproduce is his Sharpe of about 1.4.

## Final round after the sealed test (`final_checks.py`, development 2015–2026 only)

The sealed 2010–2014 test failed net and passed gross (`../prereg/own_fx_basket.md`). The
expert's last checks:
- **Cheaper pairs at ECN costs.** The region (previous close, 0.4%, 36 variants), with no
  entries 17:00–17:20 New York:
  - EUR+AUD+NZD: +211 bp/yr, 9/12 years, 0.43× return per max drawdown
  - EUR+GBP+AUD: +116 bp/yr, 9/12 years, 0.46×

  The second just clears the +100 bp bar, but only in development. There is no sealed
  data left for this family.
- **12-month dollar-trend filter (fixed in advance):** +29 and about 0 bp/yr. It removes
  the big reversal winners. Not adopted.
- **2008–2009 futures before costs:** −92 and −548 bp. The crisis losses are a trend
  problem, not a cost problem.
- **His trigger candidates** (stop 30, exit 17:15 New York, HistData spreads):
  - Envelopes on H1 SMA50/100: all lose steadily, 19% Mondays, 2022/2021 ratio 1.1–2.7×
  - the Asian-range fade at the London open: all lose steadily, 18% Mondays, ratio 1.0–1.9×

  Not his.

**Closed.** The fade pattern is real (gross positive in every year 2010–2026) but thin,
about 1.5 bp per leg. It lives on a few big reversals a year and loses in persistent
trends. Net, it is marginal even at ECN costs.
