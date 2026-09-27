# Pre-registration: supply/demand zones with a refined stop (futures)

Written and committed before `explore_fut/structure_refined.py` is first run.
Nothing below is revised after seeing results.

## Why this test

The method is market structure plus supply and demand, from the videos in
`explore_fut/`, traded on gold and four currency futures (GC, E6, B6, A6, J1) on 5-minute data.

Development results so far (`explore_fut/NOTES.md`) show two things:
- **Placing a limit order at the zone has no edge.** The hit rate tracks the
  break-even rate at every planned reward:risk.
- **Waiting for confirmation inside the zone destroys the 1:3.** It cuts the
  median planned reward:risk from 4.0 to 1.3, because the stop still sits beyond
  the swing extreme.

His process can only produce both his entry and his 1:3+ if the stop moves up to
the small 5-minute swing after confirmation. This is that version. If it is also
null against its control, the mechanical test of his documented method is done.

## Rules (frozen)

| step | rule |
|---|---|
| setup | `structure.py`: 1-hour break of structure on a close; zone = the 30-minute base at the impulse's swing extreme, with an imbalance, untouched at the break |
| trend | the 4-hour structure (same logic, closed bars only) agrees with the 1-hour break |
| zone width | at least 0.3 × the 30-minute ATR(14) |
| news | skip if the impulse's origin bar is within 30 minutes of an FOMC decision (14:00) or payrolls (08:30, first Friday). CPI and foreign central banks are not covered |
| expiry | the setup is cancelled by a trend flip, after 5 days, or at Friday 17:00 New York |
| trigger | after the first touch of the zone, a 5-minute close beyond the latest 5-minute swing (2 bars each side) formed since the touch. Entry is at that close. If the original stop (beyond the swing extreme) trades first, the setup is cancelled |
| stop | 1 tick beyond the pullback's extreme between the touch and the trigger. **Floor:** if that is closer than 1 × the 5-minute ATR(14), widen the stop to 1 ATR |
| target | the impulse extreme; skip if the planned reward:risk at entry is below 3 |
| exit | first of: stop (checked before target within a bar), target, or 10 days at the close |
| costs | 2 ticks round trip (spread and commission) plus 1 tick of slippage on stop exits |

## Control

For each trade, draw 20 random 5-minute bars:
- same market and hour of day
- same direction, with the 4-hour trend agreeing
- seed 7

Each draw enters at that bar's close. Its stop and target sit at the same
distances as the real trade's, measured in 5-minute ATRs, with the same exits
and costs. This separates supply and demand from generic trend-following.

## Tests and decision rules

Standard errors cluster by calendar week. Trades last days, and four of the
five markets are dollar pairs, so trades in the same week are correlated.

**A. The refined-stop trade against its own controls.** The statistic is the
mean over trades of (trade R − the mean R of its 20 controls).
- Development (2021-01 to 2025-03): pass if the difference is > 0 with t ≥ 2.0.
- Holdout (2025-04-01 to 2026-09): pass if the difference is > 0 with t ≥ 1.65
  (one-sided).

**B. The 5–8 planned reward:risk lead.** This comes from the limit-order version
(`structure.py`, unchanged rules). In development it made +0.60R on 128 trades,
but that bucket was chosen after seeing results. On the holdout, apply 1 extra
tick of stop slippage. Pass if mean R > 0 with t ≥ 1.65.

**The holdout is read once**, after A has run on development, whatever A's
development result. Unlock with `HOLDOUT_UNLOCK=final-evaluation`. Results go
below, unedited.

A method passes only if it passes on the holdout.

## Results

(to be filled in after the runs)
