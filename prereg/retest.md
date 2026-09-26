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

### Amendment 1 — 2026-09-25, after the random-walk check, before any real data

**The random-walk check failed the registered outcome, as it was built to.** On
simulated driftless walks, where levels mean nothing, the outcome measured from
the level price showed a mechanical pass-through:

| steps per bar | real | fake | real − fake |
|---|---|---|---|
| 10 (6,000 paths) | −0.0119, t −5.3 | −0.0195, t −7.6 | **+0.0076, t +2.23** |
| 100 (6,000 paths) | −0.0056, t −2.6 | −0.0024, t −1.0 | −0.0032, t −1.0 |

The cause is **crossing overshoot**: a path observed in steps is first seen
beyond a level, never exactly on it, so scoring from the level price counts the
overshoot as pass-through. It shrinks with resolution by about √10 per tenfold
more steps, as it should. Worse, the fake-level control did not cancel it: at
coarse resolution real minus fake passed the primary test (t = 2.23) on pure
noise, in the direction the hypothesis predicts. Real data lies at an unknown
resolution between these, so this outcome cannot carry the primary test.

**Changes:**

1. **The primary outcome is now measured from the touching bar's close:**
   `a_k = side × (close k bars after the touching bar − close of the touching bar) / ATR14`,
   positive = held, k = 12 primary, 6 secondary. The retest is identified using
   data up to that close, and a random walk's later moves are independent of it,
   so this outcome is unbiased at any resolution. It is also what a trader who
   waits for the touching bar to close would earn.
2. **The registration's argument against this was wrong.** What is biased is
   scoring the touching bar's *own* close against the level. Scoring the move
   *after* that close is not.
3. **What it gives up:** any bounce completed inside the touching bar itself.
   A level acting as a barrier should keep showing up after the bar closes.
4. **The from-level outcome** is kept as a secondary, reported only as real −
   fake, with the caveat above.
5. **The strengthening comparison** — does a level hold better on the retest
   than on the first touch — is measured as (real retest − fake retest) −
   (real first touch − fake first touch), using the primary outcome, so any
   remaining mechanics cancel.

**The random-walk check on the new primary outcome passes:**

| steps per bar | paths | seed | real | fake | real − fake |
|---|---|---|---|---|---|
| 100 | 6,000 | 11 | −0.0011, t −0.5 | +0.0016, t +0.7 | −0.0028, t −0.9 |
| 10 | 12,000 | 12 | −0.0023, t −1.5 | +0.0012, t +0.7 | −0.0035, t −1.5 |
| 10 | 12,000 | 13 | −0.0007, t −0.5 | −0.0022, t −1.3 | +0.0015, t +0.7 |

A first run at 10 steps with seed 11 showed the fake level at t −2.10 and real −
fake at t 1.93. It did not reproduce on two fresh seeds with twice the paths, and
the outcome is unbiased by construction, so it is recorded as chance. It is
reported here because it was seen.

The primary test is otherwise unchanged: real minus fake, t > 1.96.
