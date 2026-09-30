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

Pre-registration committed in 56c3f22. Development was run, then the holdout
was read once, on 2026-09-30. Net bp per trade; ± is a week-clustered standard
error.

| | period | trades | win | gross bp | net bp/trade | verdict |
|---|---|---|---|---|---|---|
| all three | development | 8,989 | 55% | +0.61 | −1.60 ± 0.08 (t −20.2) | **FAIL** |
| all three | holdout | 2,931 | 48% | +0.27 | −1.94 ± 0.13 (t −15.0) | **FAIL** |

Each cross, development → holdout, net bp:
- EURGBP: −1.00 → −1.14
- EURCHF: −1.40 → −1.26
- AUDNZD: −2.35 → −3.31

Every year is negative, 2026 included (−2.54).

**There is a small reversion before costs, far smaller than the cost.**
- Gross, the fade makes +0.6 bp per trade in development and +0.3 in the holdout.
- Entering 3 minutes late barely changes it (+0.55), so it is not stale prices.
- Breaking even needs round-trip costs under ~0.6 bp, about half a pip all-in on
  EURGBP. That is below retail and most ECN costs in the Asian session.

Part of even that gross figure may be bid-ask bounce. Exits trigger on a trade
printing through the target, which favours prints on the right side of the spread.

Bollinger(10) and Bollinger(40) are the same. "Your edge is infra" is the only way
this family could pay.

### Added after the verdict: published broker costs (exploratory)

The registered costs (1.5 / 3 / 2 pips) were assumed, not looked up. Published
costs (checked 2026-09-30) are lower:
- **IC Markets Raw:** $7 per 100k round trip; average raw spreads of 0.1 pips on
  EURGBP and EURCHF and 0.6 on AUDNZD.
- **Pepperstone Razor:** the same commission; EURGBP averages 0.3–0.4 pips.
- **Interactive Brokers:** 0.2 bp per side, plus the spread.

That is about 0.5–0.75 bp round trip on EURGBP and EURCHF, and 1–1.6 bp on AUDNZD.
The published spreads are averages over all hours. Overnight and near rollover
they are wider, which we approximate as 3×. Net bp per trade:

| costs | all 3, dev / holdout | EURGBP + EURCHF only, dev / holdout |
|---|---|---|
| ECN, average spread | −0.42 / −0.76 | −0.04 / −0.04 |
| ECN, night spread ×3 | −0.95 / −1.29 | −0.26 / −0.26 |
| IBKR, average spread | −0.05 / −0.39 | +0.19 (t 2.1) / +0.18 (t 1.7) |
| IBKR, night spread ×3 | −0.58 / −0.92 | −0.03 / −0.04 |

At the cheapest costs, the two tight crosses are roughly break-even. In the single
best case (IBKR, average spreads) they are slightly positive. Three things work
against that best case:
- The two crosses were chosen after seeing the results.
- Average spreads understate the overnight spreads.
- The gross figure may carry some bid-ask bounce.

The verdict stands. Costs, not the signal, decide this family.
