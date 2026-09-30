# Pre-registration: long-only mean reversion on NQ 3-minute bars

Written and committed before `explore_nq/mr.py` is first run on real data. The
simulator has only been run on hand-built days (`tests/test_nq_mr.py`). Nothing
below is revised after seeing results.

## Source

@MrMilkTrading posted the rules below on X, with the note: "I am NOT confident in
this yet … likely very sensitive to regime changes." A reply said that the system does
the things a mean-reversion system should do, and suggested scaling in: half at the
signal and more 0.5 ATR lower. The reply said this tends to raise the win rate to
70–75%.

## Rules (frozen, as posted)

| step | rule |
|---|---|
| market | NQ, 3-minute candles, back-adjusted continuous 1-minute data from MarketParquet |
| window | 9:00–11:00 CT = 10:00–12:00 New York. Signals come from candles that close 10:03–11:57. Long only, one order or position at a time |
| filter | efficiency ratio of the last 15 closes ≤ 0.35 (\|C − C₋₁₅\| / Σ\|ΔC\| over the same 15 changes). The indicators run on the continuous 24-hour series |
| entry | at the candle's close, a buy limit at close − 1.0 × ATR(14) (Wilder, 3-minute). Filled only if price trades 1 tick (0.25) through the limit. Cancelled after 9 minutes |
| target | the middle of the signal candle, (high + low) / 2, as a limit that needs 1 tick through |
| stop | 1.5 × ATR below the fill |
| time | exit 15 minutes after the fill; flat at 12:00 New York |
| costs | 1 tick of slippage on stops and market exits (his rule 7); **plus $4.50 round-trip commission (0.225 points)**, which he does not mention |

**The one deviation we can't avoid.** He fills on 1-second data and has 1-minute
bars. Inside a minute, the order of events is unknown. We take the losing order, as
his rule 7 does:
- the stop is checked before the target
- scale-in adds fill before the stop is checked
- no target is credited in the minute of the fill

Time exits happen at the open of the minute 15 minutes after the fill minute.

**B. Scale-in variant (from the reply).** The same signal places two limits: half
the position at close − 1.0 ATR and half at close − 1.5 ATR. The second limit stays
live until the position exits. The position opens on the first fill, and the stop,
target and clock are the same as in A. A trade where only the first half fills
risks half the size. Max exposure matches A.

## Periods

- Development: 2021-01 to 2025-03-31.
- Holdout: 2025-04-01 to the end of the archive (2026-09). It is sealed by
  `lib/holdout.py`, and unlocked once with `HOLDOUT_UNLOCK=final-evaluation` after
  development has run, whatever the development result. The holdout was already
  read for GC and currencies (`fut_zone_refined.md`), but **NQ has never been read
  in this repo** in either period.
- The rules were posted in 2026 and were presumably tuned on recent data. So our
  holdout may sit inside his sample. Our development period is the better
  out-of-sample test of *his* choices. Both periods have to pass.

## Tests and decision rules

Units are NQ points per trade, net of all costs. The standard error clusters by
calendar week.

**A1. Profitable as posted.**
- Development: mean net > 0 with t ≥ 2.0.
- Holdout: mean net > 0 with t ≥ 1.65.

**A2. The entry beats random long entries.** For each A trade, 20 market buys at
random minutes of the same day's 10:00–12:00 window (seed 7). Each has:
- entry at the minute's open + 1 tick
- A's target and stop distances in points
- the same time stop, 12:00 flat, fill-minute rule and costs

Statistic: mean of (trade − mean of its controls).
- Development: t ≥ 2.0.
- Holdout: t ≥ 1.65.

This separates the rule from being long NQ in 2021–2026.

**B. Scale-in.**
- Same thresholds as A1.
- Reported alongside, with no verdict: the win rate and the max drawdown of cumulative
  net points, against A's.

A system passes only if it passes on the holdout.

## Reported without verdict (sensitivity)

- Gross of commission (his framing).
- Optimistic fill minute: target credited in the fill minute.
- No efficiency-ratio filter, to see whether the regime filter does work.

## Results

(Not yet run.)
