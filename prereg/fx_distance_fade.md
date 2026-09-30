# Pre-registration: fading a fixed 1% distance from the 4-hour average (FX futures)

Written and committed before the holdout is read for this rule.

## Where it came from

An X post described "the best mean reversion strategy I've ever built":
- multi-asset FX
- one timeframe, with the same parameters and management everywhere
- one specific parameter, "literally just one rule"

It showed an MT5 equity curve from 2018 to 2026. The curve's x-axis counts trades,
and its trades bunch in the volatile stretches (2022, early 2023, 2025–26). They
nearly stop in calm 2021.

`explore_fx/one_rule.py` tested 63 one-rule variants on development data
(2021-01 to 2025-03). Only fixed-threshold rules reproduce that timing. Rules
scaled to volatility (RSI, Bollinger, N-bar, IBS, ATR-scaled) trade as often in
2022 as in 2021. The best of the 63 on Sharpe is the rule below. **It was chosen
after seeing all 63 results**, which is why it needs this holdout.

Development: 574 trades, 66% winners, +0.31 ATR per trade, Sharpe 0.99, trade-level
t 2.86, every year positive.

## Rule (frozen)

| step | rule |
|---|---|
| markets | E6, J1, B6, A6, N6, E1 (CME currency futures, back-adjusted 5-minute bars) |
| bars | 4-hour bars, aligned to the 17:00 New York FX day |
| entry | at a bar's close, if the close is > 1% above its 20-bar SMA, short at the next bar's open. If it is > 1% below, go long |
| exit | at the next bar's open after a close back across the SMA |
| one position per market; no stop | |
| cost | 1.5 ticks per round trip |
| unit | return per trade in ATR(20) at entry, so markets carry equal risk |

## Test

Holdout: 2025-04-01 to 2026-09. Read once with `HOLDOUT_UNLOCK=final-evaluation`.

**Pass** if the mean return per trade is > 0 with t ≥ 1.65, clustered by calendar
week (the six markets mostly move with the dollar).

The 0.5% and 2% neighbours are reported alongside, with no verdict.

## Results

Pre-registration committed in 000e5b6, then the holdout was read once, on
2026-09-30. A missing import was fixed first; it had crashed before loading any data.

| | trades | win | mean ATR/trade (week-clustered) | Sharpe | verdict |
|---|---|---|---|---|---|
| development, 1% | 574 | 66% | +0.308 ± 0.143 (t +2.15) | 0.99 | chosen from 63 |
| **holdout, 1%** | 141 | 68% | **+0.244 ± 0.339 (t +0.72)** | 0.63 | **FAIL** |
| holdout, 0.5% | 449 | 62% | +0.058 ± 0.206 (t +0.28) | 0.35 | — |
| holdout, 2% | 14 | 50% | −0.674 ± 0.583 (t −1.16) | −1.00 | — |

The development t of 2.86 quoted above assumed independent trades. Clustered by
week, as the currencies move together, it is 2.15.

**Not confirmed, and not refuted either.**
- The holdout has the same sign, a similar size (+0.24 against +0.31) and the
  same win rate as development. But it has only 141 trades, and it is well within
  noise.
- It made money through 2025 Q3 and gave back 20 ATR in 2026 Q1.
- The 0.5% neighbour is flat, and the 2% neighbour is negative.
