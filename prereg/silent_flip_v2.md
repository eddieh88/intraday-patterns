# Pre-registration: the silent flip, version 2

Written before any version-2 code exists and before any data is read under these
rules. Version 1 (`silent_flip.md`) failed in development and stays a fail. This
is a new specification, not a rescue: it changes the three definitions that his
own worked example shows were stricter than his reading. Changes after this are
dated amendments made before the data they concern is read.

## Why a version 2

His live day was identified as **Thursday 2026-09-03**:
- his chart is timestamped "ons 2 sep. 2026 21:30" (Swedish time), and
- on Yahoo 15-minute bars, the prior-day levels match his to the cent (PFE 29.09 /
  28.70, UBER 77.23–77.24 / 75.36).

On that day he skipped XOM, BAC, NVDA and PFE, and shorted UBER at 77.78 with a stop at
78.50 and the target at 75.36. Version 1 agrees on the four skips but misses the UBER
trade, for three reasons:
1. **Flip high.** His was 78.21: the Aug 31 09:30 bar (78.29 on Yahoo), which
   gapped down from Aug 28's close. Version 1's swing rule compares neighbours
   across days, so a gap-down opening bar is never a swing. Version 1 took 79.00.
2. **Tolerances in ATR15.** ATR15 comes from yesterday's afternoon bars, which are
   a fraction of an opening bar. PFE's 4¢ miss of the range low is 0.52 ATR15, and
   UBER's candle 2 high exceeds version 1's break allowance by 0.4¢.
3. **The silent candle.** UBER's candle 2 opened at 78.15 and closed at 78.16 on
   Yahoo, green by one cent. He read it as red "by a few points".

## What changes from version 1

| | version 1 | **version 2** |
|---|---|---|
| flip high / low | most recent swing beyond RH / RL; neighbours may come from adjacent sessions | most recent swing beyond RH / RL, 2 bars each side, **neighbours only from the same session**, so a session's first or last bar can be a swing |
| "tests the level" | high within 0.25 × ATR15 of L | high within **0.10 × candle-1 range** of L |
| candle 2 color | strictly opposite | opposite, **or flat: close no more than 0.05 × candle-1 range against the expected color** |
| candle 2 may not break | more than 0.1 × ATR15 beyond L and candle 1's extreme | more than **0.10 × candle-1 range** beyond |
| stop buffer | 0.1 × ATR15 | **0.10 × candle-1 range** |

Everything else is as in version 1:
- universe and bars
- RH / RL (yesterday's RTH high and low)
- candle 1: range ≥ 1.0 × ATR15, body ≥ 0.6 × range
- candle 1 closes back inside L
- entry: a stop order at candle 2's extreme, live 10:00–10:25, cancelled if the
  stop trades first
- target: the opposite range level
- exits and the in-bar conservative rule
- 3 bp costs
- one trade per name per day

## A check against his day, before any archive data

Run on Yahoo 15-minute bars for 2026-09-03, with execution on the same 15-minute
bars. Version 2 must:
- take UBER short, with the trigger at 77.78, the stop within 5¢ of his 78.50, and
  the target at 75.36
- produce no trade in NVDA, PFE, XOM or BAC

If it does not, the definitions are corrected by dated amendment before anything
else runs.

## Controls, tests and holdout

As in version 1, with Amendment 2 carried over:
- **Controls:** fake levels from another session of the same name, and 20
  random entries per trade.
- **Q1, pays:** net R of real trades > 0.
- **Q2, the levels matter:** real minus fake-level net R > 0. Critical t is
  **2.75** in development (Amendment 2 of version 1).
- **Q3, the timing matters:** real minus random-entry net R > 0. Its known
  conservative bias of about −0.04R is reported, not corrected.
- **A pass in development** needs all of:
  - t at or above the critical value in the primary specification
  - positive in at least 3 of the 4 blocks
  - positive in at least 2/3 of the grid
- **Holdout:** once, only for what passes; t ≥ 1.65 (Q2: 2.26).

**Robustness grid (81 cells):**
- candle-1 body share: 0.5, 0.6, 0.7
- test tolerance: 0.05, 0.10, 0.20 × candle-1 range
- flat allowance for candle 2: 0, 0.05, 0.10 × candle-1 range
- target: opposite range level; nearer range level; 2R

The strength threshold is dropped from the grid: in version 1 it changed almost
nothing, because opening bars dwarf ATR15.

**Random-walk check:** the version-2 pipeline at 1,000 names, two seeds. Q2 and
Q3 must not show a bias in the setup's favour beyond 2 standard errors.

## Reported, no verdict

As in version 1, and also the frequency his claim can be compared with:
- setups per stock per month while in the top 100, and the share of stock-days
  with a setup (formed) and with a fill
- the number of the top 100 that set up on a typical morning
- trades per day for a 5-stock and a 100-stock scan

## Prior

**Negative.** Version 1's 877 trades were zero before costs, and its fake levels
did as well as the real ones. Version 2 will find several times more setups, closer
to his rate. The question is whether the setups his eye takes, and version 1 did
not, behave differently.

## Amendment 1 — 2026-10-05, before any archive data under version 2

**His-day check: PASS.** On Yahoo 15-minute bars for 2026-09-03:
- **UBER:** short at the flip high (78.29), trigger 77.78, stop 78.48 (his 78.50),
  target 75.36. It fills in the 10:00 bar (he entered at 10:07) and reaches the
  target, +3.45R gross.
- **NVDA, PFE, XOM, BAC:** no setup, as he called them.

**Added, reported with no verdict:** a trailing stop closer to how he managed his
live trade. He moved the stop three times as the trade worked: to the day's open,
then twice to just above recent small highs on a 1-minute chart. Approximation:
once the trade is +1R, the stop follows the extreme of the last three 5-minute
bars. Version 1's trail (break-even at +1R, then the last 15-minute bar) is
reported too. The verdicts stay on the fixed stop.

**Added for review:** every version-2 trade is written to a file, and a random,
outcome-blind sheet of them is rendered for checking by eye.

## Amendment 2 — 2026-10-05, before any archive data under version 2

**The random-entry control had a look-ahead (in version 1 too).** Its 20 entries
were drawn from all of 10:00–10:25, but only on days when the real stop order
filled. An entry drawn before the fill bar "knows" that price later reached the
trigger, which favours the control. On random walks the control averaged about
+0.08R gross, against −0.007 ± 0.012R for brackets of random direction with the
same exits. That, more than the conservative fill rule, is why version 1's Q3
leaned against the setup. Version 1's Q3 fail stands, since the bias only made it
harder to pass. **Fix for version 2:** the random entries are drawn only from the
real trade's fill bar onward, the "after-only" rule from E16.

**Random-walk check, version 2 (1,000 names):**

| seed | real net R | Q2 real − fake | Q3 real − random |
|---|---|---|---|
| 13 (control before the fix) | +0.060 (t 2.04) | +0.060 (t 1.57) | −0.025 (t −1.80) |
| 21 (fixed control) | −0.033 (t −1.22) | −0.043 (t −1.15) | −0.019 (t −1.42) |

Q2 and Q3 pass on both seeds. **Q1 on seed 13 would have passed at t ≥ 2.0 with no
edge at all.** The two seeds average about +0.01R net, so seed 13 was chance. But the
standard errors here run about 1.37× too small, as version 1's seven null runs
showed for Q2. **Change: Q1's critical t is 2.75 in development (holdout 2.26),
the same as Q2's.** Q3 stays at 2.0, since its remaining lean is against the setup.
