# Pre-registration: the evening dollar-basket fade on EURUSD, AUDUSD and NZDUSD (2010–2014)

Written and committed before any 2010–2014 data is read. The spot files for 2010–2014 were
downloaded on 2026-09-30 and sealed (`lib/holdout.py`, `EARLY_UNLOCK`). Only their names
have been checked for completeness. Nothing below changes after the run.

## Where it came from

The rule came out of the search for the FX strategy behind a posted MT5 curve (see
`explore_fx/NOTES.md` and the shared document). It is a sibling of his, found because his
clues pointed at the family. The timing and weekday evidence say it is not his
implementation.

In development, `explore_fx/basket_match.py` scored 3,600 variants on 2018–2026 spot data.
One region reached about 1× return per max drawdown a year (0.8–1.37× across neighbours):
EUR/USD + AUD/USD + NZD/USD, measured from the previous close, with a 0.4% threshold.

`explore_fx/basket_wf.py` then ran a walk-forward:
- **Re-choosing settings each year has no edge:** single best −38 bp a year, top-10 average
  +29 bp a year.
- **The fixed region:**
  - in-sample 2018–2026: +257 bp a year, 7 of 9 years positive
  - 2015–2017, which were not used to find it: +453, −67, +77 bp
- **The region depends on a few big trades.** Over 2015–2026 the region is +201 bp a year.
  Removing the 3 best entries each year turns it into −86 bp a year (3 of 12 years positive).
  It lives on a few sharp dollar reversals a year.

## Rule (frozen): an equal-weight portfolio of 36 variants

| part | rule |
|---|---|
| pairs | EURUSD, AUDUSD, NZDUSD (HistData spot, 1-minute bid/ask) |
| FX day | 17:00–17:00 New York. No trading 17 Dec – 5 Jan |
| reference | the previous FX day's close: the last mids before 17:00 New York (Friday's on a Monday) |
| basket | the mean of the three pairs' % moves from the reference, signed so + = USD stronger |
| entry | from 17:00 New York for W hours: the first minute with \|basket\| ≥ 0.4% and every pair's spread filter OK (spread ≤ 3× its median over the loaded period and ≤ its previous-4-minute mean). Fade the dollar on all three pairs at that minute. One group per FX day |
| exit | per leg: a stop of S pips, no target; close at clock C (the first after entry) |
| variants | W ∈ {6, 8, 10} h × C ∈ {17:00 London, 11:00 New York, 16:55 New York} × S ∈ {25, 30, 40, none} = 36 |
| execution | buys at the ask, sells at the bid; stop checked before the clock in each minute |
| P&L | per variant, each group = the sum of its three legs in bp ÷ 3. The portfolio = the mean of the 36 variants' daily P&L (1× notional per leg, one unit of capital per group) |

This is exactly `explore_fx/basket_match.py` with these settings. The holdout run is
`explore_fx/basket_holdout.py`.

## Decision rules (spot, 2010–2014, net of the HistData spread)

Measured on the portfolio's daily P&L in bp.
- **PASS:** mean ≥ +100 bp a year, at least 3 of 5 years positive, and return per max
  drawdown ≥ 0.4× a year.
- **FAIL:** mean ≤ 0, or at most 1 year positive.
- **INCONCLUSIVE:** anything in between. Reported as that.

## Reported alongside (no verdict)

- **Gross (at the mid, no spread):** separates a cost-driven fail from a no-edge fail.
  2010–2014 spreads were wider than today's.
- **Split:** 2010–2012 (including the euro crisis) against 2013–2014 (calm).
- **Year by year,** and the total with the 3 best entries per year removed.
- **CME futures, 2008–2014** (EUR, AUD and NZD futures, 5-minute bars, the same rule on
  trade prices, 1 pip round trip per leg). A cross-check of the pattern only. It cannot
  rescue a spot fail.

## Results

(Not yet run.)
