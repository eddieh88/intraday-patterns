# Pre-registration: an Asian-session night scalper on three FX crosses

Written and committed before `explore_fx/night.py` is run on real data. It has only
been run on hand-built nights (`tests/test_fx_night.py`).

## Where it came from

The author of the FX curve in `fx_distance_fade.md` later added:
- "3 x FX pairs"
- "super simple, indicator-based"
- "has stops (no pyramiding) and closes at the end of each day"
- a spread filter is "one of the most important things"; skip when the order book is thin
- a "stale position check" for bank holidays

Someone replied "your actual edge is infra". That profile fits the classic
night scalper: fade an indicator band on quiet crosses in the Asian session, and be
flat before London. This tests the idea on our data. It is not his rule.

## Rules (frozen)

| step | rule |
|---|---|
| crosses | EURGBP = E6/B6, AUDNZD = A6/N6, EURCHF = E6/E1 (CME futures, 1-minute). A minute is used only if both legs traded in it |
| bars | 5-minute bars of the cross; Bollinger(20, 2) on their closes |
| entry | a 5-minute bar closing 18:15–01:00 New York, on Sunday–Thursday nights. A close above the upper band → short; below the lower band → long. Entry at the cross price of the first both-traded minute after the bar closes |
| target | the signal bar's middle band; exit at the first 1-minute close through it |
| stop | 2 × the entry's distance from the target, on the other side; exit at the first 1-minute close beyond it |
| time | flat at the first minute at or after 02:00 New York |
| positions | one per cross; the next signal must come from a bar closing after the exit |
| costs | spot-like Asian-session round trips: EURGBP 1.7 bp, AUDNZD 2.8 bp, EURCHF 2.1 bp (≈ 1.5 / 3 / 2 pips) |
| unit | bp of price per trade |

**What we can't test:**
- **His spread filters.** We have trades, not quotes.
- **Spot fills.** Futures in the Asian session are thinner than spot. Our costs are
  set to spot-like levels, so a pass would still need spot tick data to believe.

## Periods and decision rule

Development 2021-01 to 2025-03; holdout 2025-04 on, read once. The FX holdout was
read before for a different rule (`fx_distance_fade.md`), not for this one.

Net bp per trade, pooled over the three crosses, clustered by week.
- **Development:** pass if the mean > 0 with t ≥ 2.0.
- **Holdout:** pass if the mean > 0 with t ≥ 1.65.

## Reported without verdict

- **Gross of costs**, and the cost at which it breaks even.
- **Each cross on its own.**
- **Entry 3 minutes late.** If the edge disappears with a two-minute delay, it was
  stale prices, not reversion.
- **Bollinger(10, 2) and Bollinger(40, 2).**
- **By year.**

## Results

(Not yet run.)
