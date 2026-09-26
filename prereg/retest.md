# Pre-registration — does a level hold on the retest?

Written 2026-09-25, before the detector exists and before any outcome of this
design is measured. Changes require a dated amendment below, made before the
result they would affect is seen.

## The hypothesis

> **When price returns to a level it has already touched, it bounces off it:
> the move after the retest goes opposite to the move into it.**

It applies from either side. Rising into a level from below, the level holds as
resistance and price turns down. Falling into it from above — including after a
break — it holds as support and price turns up. What happened after the first
touch does not matter; the claim is about the bounce on the second.

## What earlier work did and did not test

E11 compared reactions at levels with reactions at random prices and found no
difference — but only on the **first** touch, and only from below. The trader's
claim is that a level proves itself on the first touch and pays on the retest.
That is untested here.

## Definitions

All prices are 5-minute bars stamped at their start. Regular hours end at 16:00,
or 13:00 on a detected early close.

| term | definition |
|---|---|
| **levels** | For each name-day, known before 09:30: prior session high and low; high and low of the session two days back; pre-market (04:00–09:25) high and low. Levels within 0.1% of each other are merged, keeping the first in that order. |
| **touch** | a bar whose low ≤ level ≤ high |
| **first touch** | the first regular-hours touch, on a bar stamped 14:30 or earlier |
| **move away** | after the first touch, some bar's high or low reaches at least **0.18%** from the level, and at least **3 bars** separate first touch and retest |
| **retest** | the first touch after the move away, on a bar stamped 15:00 or earlier, with 12 more bars in the session |
| **approach** | the side price came from: the close of the bar before the touching bar, relative to the level. Above means falling into it; below means rising into it. Equal: skipped. |
| **outcome** | **bounce_k** = (close k bars after the touching bar − level) / ATR14, **signed so positive = opposite to the approach**, i.e. the level held. k = 12 (60 min) primary, 6 secondary. |
| **ATR14** | mean daily regular-hours range over the prior 14 sessions |

The outcome is measured from the **level price**, not the touching bar's close:
a bar that touches a level from below usually closes back below it, which would
count as a bounce from the close whether or not the level meant anything.

## The control

For every real level L a **fake level** is placed at the same distance from the
09:30 open on the opposite side: F = 2 × open − L. The identical detector and
outcome run on it. Fakes within 0.1% of any real level are dropped. Price comes
back to *any* price some of the time and bounces some of the time; the fake
level measures how much.

## Before any real data: the random-walk check

The detector first runs on simulated driftless random-walk sessions with the
same bar count, volatility and level construction. There, levels mean nothing
by construction. **Real and fake bounce_12 must both be within 2 standard errors
of zero, and of each other.** If not, the design has a mechanical bias and is
fixed — by amendment — before real data is read.

## Data

Point-in-time universe, each day's top 100 (`cache/intraday_pool.parquet`).
**Development period only:** 2021-01-19 → 2025-03-31. The holdout
(2025-04-01 → 2026-09-21), sealed by `lib/holdout.py`, is read only as
described under *Confirmation*.

## The test

**Primary — one test, critical value 1.96:**

> mean bounce_12 at **real** retests minus mean bounce_12 at **fake** retests,
> with a session-clustered standard error.

- **SUPPORTED** if the difference is positive with t > 1.96.
- **NOT SUPPORTED** otherwise.

**Secondary — reported, no verdict:**
- the same at k = 6;
- the share of retests that held (bounce > 0), real vs fake;
- by level type, six of them (Bonferroni-adjusted t reported);
- **does testing strengthen a level?** Real retests vs real *first* touches,
  with first touches scored the same way;
- counts at every stage of detection.

## Confirmation

Only if the primary is SUPPORTED on development data: the identical code runs
**once** on the holdout. Confirmed if the difference is positive with t > 1.96
there too.

If NOT SUPPORTED, the holdout stays sealed.

## What comes after, if anything

A supported bounce is not yet a trade. A trade — entry at the level on the
retest, a stop beyond it, costs — would get its own registration, written
before it runs. This study asks only whether the level holds more than a random
price does.

## Known limitations, stated in advance

- **Levels are the pre-open kind only.** Intraday swing highs and lows, round
  numbers and multi-week levels are not tested.
- **5-minute bars.** A touch inside a bar can't be ordered against the bar's
  other extreme.
- **The move-away and separation rules are fixed at 0.18% and 3 bars** — the
  values that fixed error 02 — not tuned here.

## Amendments

*None.*
