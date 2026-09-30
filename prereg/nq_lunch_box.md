# Pre-registration: the NQ "Lunch Box" scalp

Written and committed before `explore_nq/box.py` is run on real data. The simulator
has only been run on hand-built days (`tests/test_nq_box.py`).

## Source

@MrMilkTrading said this is "what I was originally going for" with the posted
algorithm (`nq_mean_reversion.md`, failed): "NQ enters a 'Lunch Box' (Slop Box) in
the PM. Bounces around a stupid 30-40 point range." His chart marks
"20 point scalps" from the bottom of the box to the top. His tips:
1. look at the higher timeframe for bias
2. don't wait for your stop to hit, get out quickly
3. keep an eye on SPX, which will often break out of its box together with NQ
4. buy the bottom of the box, sell the top, not the reverse

## Rules (frozen)

| step | rule |
|---|---|
| box | NQ's 12:00–12:30 New York range, h = high − low. Trade the day only if h ≤ 15 bp of price and h ≥ 10 points. At 2026 prices, 15 bp ≈ 40 points, his range. That is about the narrowest 10–20% of days |
| entry | 12:30–15:00. Buy limit at low + 0.1h; short limit at high − 0.1h. Each fills only on trading 1 tick through. One position at a time. After an exit, price must trade through the box middle before the next entry |
| target | 0.5h from the entry (his "20 point scalps" in a 30–40 point box) |
| quick exit | a 1-minute close outside the box exits at the next minute's open (tip 2). The box then dies: no new entries that day |
| hard stop | 0.25h beyond the box edge |
| time | flat at 15:00 |
| intrabar | the stop is checked before the target; no target in the minute of the fill |
| costs | 1 tick of slippage on stops and market exits, 0.225 points commission |

**Variants.**
- **B (tip 1):** trade only in the direction of the daily trend. That is the prior
  16:00 close against its 20-day average: above means longs only, below means
  shorts only.
- **C (tip 3):** ES's own 12:00–12:30 box. A 1-minute ES close outside it also exits
  the NQ position and kills the NQ box.

## Periods

- Development: 2021-01 to 2025-03.
- Holdout: 2025-04 onward, read once after development, whatever the result.

**Disclosure.** The NQ holdout was already read for the posted algorithm. Before
these rules were written, the 12:00–12:30 range sizes were looked at, in both
periods, to translate "30–40 points" into basis points. No outcome of any box
trade has been seen.

## Decision rule

Net points per trade, with the standard error clustered by week.
- **A** passes if development mean > 0 with t ≥ 2.0, and holdout mean > 0 with
  t ≥ 1.65.
- **B** and **C** are judged by the same rule.

A variant passes only if it passes on the holdout.

## Results

(Not yet run.)
