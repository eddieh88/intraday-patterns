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

## Results — development, 2026-10-05

`python3 flip/run.py dev 2 && python3 flip/analyze.py dev 2`. Primary
specification: **1,388 real trades** on 711 sessions across 221 names, and 1,456
fake-level trades. Net R at 3 bp, session-clustered.

| question | estimate | t | years positive | grid positive | verdict |
|---|---|---|---|---|---|
| Q1 pays | −0.036 ± 0.030 | −1.20 | 1/4 | 0/81 | **fail** |
| Q2 levels matter (real − fake) | −0.026 ± 0.035 | −0.75 | 2/4 | 14/81 | **fail** |
| Q3 timing (real − random entry) | −0.029 ± 0.014 | −2.08 | 1/4 | 5/81 | **fail** |

**Nothing passes; the holdout stays sealed.** (The analysis prints a "+0.04 bias-
corrected" Q3 line carried over from version 1. It does not apply here: version 2's
control is after-only.)

- **Before costs it is zero:** −0.001R gross; −0.013 at 1 bp, −0.071 at 6 bp.
- **Exits:** 21% reach the target (median 1.7R away), 38% are stopped, 41% are
  open at the close.
- **Trailing stops do not help:** version 1's trail −0.038, the trail like his
  −0.040.
- **By level:** RH −0.021, RL −0.044, FH −0.056, FL −0.022, all within noise of zero.
  Fake levels set up as often (1,456 vs 1,388) and do no worse.
- **Frequency:** 1.32% of stock-days fill, 3.3 trades a year per stock in the top
  100, about 1.3 a day across a 100-stock scan, and about one every three weeks on a
  5-stock watchlist. That is 60% more than version 1, and still below "weekly per
  stock".
- **One trade a day, the first to fill (his scan):** 711 days, −0.050R a day
  (t −1.27), 44% of days positive.

His live day is reproduced exactly, and the rules that reproduce it lose slightly
after costs on four years of the top 100 stocks, no better than the same rules on
levels taken from another day.

## Exploratory follow-ups, development only (no verdicts, holdout untouched)

**Stop management** (`flip/exit_sweep.py`): 11 policies on the same 1,388 entries,
real and fake levels:
- fixed −0.036; break-even at +0.5R −0.016 (best, but it helps fake levels alike)
- break-even at +1R −0.030; trail 0.5R −0.022; trail 1R −0.029
- trail the last 1 / 3 / 6 bars after +1R: −0.041 / −0.039 / −0.035
- half off at +1R −0.040; exit at 11:00 −0.035; exit at 12:00 −0.033

All are negative, none beats fake levels with the same exits, and none is positive
in more than 2 of 4 years. As E8 found, moving the stop changes how results are
distributed, not their average.

**Confirmed entry** (`flip/confirm_entry.py`): wait for the third candle to close
beyond candle 2's extreme in the silent candle's color, and enter at 10:15. It
confirms on 47% of real and 50% of fake trades. As a tradable entry:
- 635 trades, −0.111R (t −3.41), negative in every year, against −0.037 for fake levels

Split after the fact (not tradable): touch entries whose third candle confirmed
made +0.180, those that did not −0.227. Fake levels show the same split (+0.268 /
−0.245). The profit of the confirmed trades happens during the third candle itself,
before confirmation can be seen.

**Where candle 1 opened** (`flip/gap_split.py`), u = position of the open from the
tested range level (0) to the opposite one (1):

| where | share | net R | t | fake | real − fake |
|---|---|---|---|---|---|
| inside (0.2–0.8): a push into the level, as in his NVDA and UBER | 74% | −0.007 | −0.20 | −0.002 | −0.006 |
| u ≥ 0.8: gap-and-reverse, as in his PFE and the GM 2021-06-02 sample | 14% | −0.068 | −1.09 | +0.032 | −0.100 |
| u < 0.2: opened at or past the tested level | 11% | −0.183 | −2.27 | +0.050 | −0.233 |

Excluding the two odd groups leaves the core pattern at break-even after costs, the
same as fake levels.

## Feature study — written 2026-10-06, before it runs (development only)

Does anything known by 10:00 pick the silent-flip trades that pay? Primary v2
trades (1,388 real, with the matching fake-level trades), net at 3 bp. All
features come from `cache/intraday_daily.parquet`. Full-session highs and lows are
rebuilt as the max/min of its 09:30–10:00, 10:00–11:00 and 11:00–16:00 blocks,
because its `pdh`/`pdl`/`hi_rth`/`lo_rth` cover 11:00–16:00 only (see below). ATR20
is the mean full-session range of the prior 20 sessions.

| feature | definition (known by 10:00) |
|---|---|
| vol regime | mean full range of the last 5 sessions / of the last 20 |
| yesterday's width | (yesterday's full high − low) / ATR20 |
| gap | \|09:30 open − yesterday's close\| / ATR20 |
| opening range | today's 09:30–10:00 range / its mean over the prior 20 sessions |
| market with the trade | the trade's side × the median 09:30–10:00 return of that day's top 100 |
| market volatility | the median across the top 100 of (full range / close), averaged over the prior 20 sessions |

**Method:** for each feature, five fifths cut at the real trades' quintiles.
Report real net, fake net (same cuts) and real − fake. That's 30 cells.

**A cell qualifies only if all hold:**
- real net t ≥ 3.0 (about 0.05 / 30)
- real − fake > 0 with t ≥ 2.0
- positive in at least 3 of the 4 development blocks

A qualifying cell is run once on the holdout as a single rule: real net > 0 with
t ≥ 1.65, and real − fake > 0. If none qualifies, the holdout stays sealed.

**Found while building this:** `data/build_daily.py` takes the prior-day high and
low from the 11:00–16:00 block alone. On 56% of days the real high or low is set
before 11:00. E2, E5, E6, E6b and E8–E11 used those columns. The headline results
(E17/E18, the retest study, the selection study, every study in `flip/` and
`stops/`) build their levels elsewhere and are unaffected. To be fixed separately.
