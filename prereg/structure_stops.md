# Pre-registration: do structural stops make the setups work?

Written before any code for this study exists. Nothing below is revised after
seeing results; changes are dated amendments made before the data they concern
is read.

## The question

E17 and E18 gave every setup the same mechanical risk unit: twice the range of
the signal bar. That answered "does the setup pick the right direction?" and
the answer was "a little, and no better than momentum". It did not test the
setups as they are taught, where the stop goes at the structure the setup is
built on: the other side of the opening range, just past the level, under the
pullback's low. The claim this study tests:

> **The setup's structure tells you where the trade is wrong.** A stop placed
> at that structure does better than a stop of the same typical width placed
> without regard to structure, and the setup traded that way pays after costs.

## What has already been seen

E1–E18 read the whole 2021–2026 sample, including the holdout below, with these
same entries and the 2-bar stop. The holdout therefore protects the
**stop-placement comparison**, which has never been run on any period. It does
not protect the entries themselves, which are already known to pick direction
weakly.

## Data

- **Universe:** each day's top 100 from `cache/intraday_pool.parquet`
  (point-in-time, prior 20 sessions of RTH dollar volume; guarded by
  `data/universe_check.py`).
- **Development:** 2021-01-19 → 2025-03-31, every session (E17 used every
  second one).
- **Holdout:** 2025-04-01 → 2026-09-21, sealed by `lib/holdout.py`. Read once,
  and only under *Confirmation* below.
- **Bars:** 5-minute RTH, stamped at bar start.
- **ATR:** mean high − low of the prior 14 RTH 5-minute bars, carried across
  sessions, so the 09:30 bar uses the prior day's last 14. Known at the signal
  bar's close.

## Entries — frozen as in `experiments/e17_close.py`

Kept exactly as E17 coded them, so the results connect to E17/E18. Signals come
from bars stamped 09:30–11:25. Long rules shown; shorts mirror.

| setup | signal bar *e* | per side per day |
|---|---|---|
| **ORB** | first close above the 09:30–10:00 high, at or after the 10:00 bar | 1 |
| **level** | pre-market (04:00–09:30) high. Break = first close above it. After the break, price advances ≥ 0.18% past the level; then, 3–15 bars after the break, a bar's low touches the level and it closes above. That bar is *e* | 1 |
| **VWAP** | previous bar closed below VWAP, this bar closes above | up to 3 |
| **pullback** | the session's high so far is > 0.5% above the 09:30 open, and bar *e* closes red | up to 3 |

The pullback and level definitions are cruder than the taught versions (the
pullback can fire after the run has reversed; any red bar qualifies). That is
known and deliberate: changing entries here would mix two questions. A
better-specified pullback is a separate study.

## The trade

| | |
|---|---|
| fill | **open of bar *e*+1**, the first price available after the signal |
| stop | one of the stop rules below, fixed at the fill |
| target | **+2R** primary, where 1R = \|fill − stop\| |
| time exit | close of bar *e*+60 (5 hours) or the session's last bar, whichever is first |
| intrabar | stop checked before target; stops and targets fill at the bar open if it gaps through |
| cost | **3 bp** round trip on the fill price, charged in R; 1 bp and 6 bp reported |
| skip | fill already at or beyond the stop; or 1R < 0.03% of price (as E17) |

## Stop rules (long; shorts mirror)

`b` is the buffer, **0.1 × ATR** primary.

**S — structural (the one under test)**

| setup | stop |
|---|---|
| ORB | 09:30–10:00 low − b |
| level | min(level, low of bar *e*) − b |
| VWAP | lowest low of the run of consecutive bars that closed below VWAP immediately before *e*, and of bar *e* itself, − b |
| pullback | lowest low from the bar after the session's high-so-far bar through bar *e* (bar *e*'s own low if *e* set the high), − b |

**C — width-matched control (isolates placement).** For each trade, its
structural width in ATR units, w = \|fill − S\| / ATR, is replaced by the w of
another trade drawn at random from the **same setup, same side, same calendar
month**. The control stop is the fill − w_drawn × ATR. 20 draws per trade (seed
7); the trade's control result is the mean of the 20. The control has the same
distribution of stop widths as S but no connection to where the structure is.
Its target is +2R on its own width, as for S.

**V — the E17 stop.** fill − 2 × (high − low of bar *e*). Reported for
continuity with E17/E18.

**M — momentum side, structural width.** Same fill, same stop distance as S,
but the side is the sign of the close of bar *e* minus the close of bar *e*−6
(the E18 k=6 rule). Where M's side equals the setup's side the trade is
identical to S. For ORB this is every trade, as in E18, and the comparison is
reported as identically zero.

## Tests

Units are net R at 3 bp. Standard errors are clustered by session. Four setups
are tested, so the critical t in development is **2.50** (Bonferroni, 0.05 / 4).

**Q1 — placement (primary).** Mean of (S − C), paired per trade.
Structure matters for that setup if:
1. S − C > 0 with t ≥ 2.50, **and**
2. S − C > 0 in at least 3 of the 4 development blocks: 2021, 2022, 2023, and
   2024 with 2025 Q1, **and**
3. S − C > 0 at every neighbour: buffer 0, 0.1 and 0.25 ATR × target 2R and 3R
   (six cells; t is not required in the five non-primary cells).

**Q2 — pays as traded.** Mean S net R. Passes if > 0 with t ≥ 2.50 and
conditions 2 and 3 above hold for S itself.

**Q3 — beats momentum as traded.** Mean of (S − M), paired. Same three
conditions. Not tested for ORB.

**Reported, no verdict:** S − V; win rate, share exiting at stop, target and
time; the median width of S and C in bp and ATR; gross and 6 bp results; ORB
with the stop at the range midpoint instead of the far side; a target at the
next level in the trade's direction (nearest of prior-day high, pre-market high
for longs) when it is at least 1R away, else 2R.

## Random-walk check — before any real data is read

The whole pipeline (signals, all four stops, the control draw, the trade
simulator) runs first on simulated sessions: Gaussian random-walk 5-minute bars
with the same count of names, sessions, bar counts and per-name volatility as
development, and a pre-market segment. There, structure means nothing by
construction, so **S − C must be within 2 standard errors of zero for every
setup.** If it is not, the design has a mechanical bias (for example, from how
the structural stop interacts with where the fill lands) and it is fixed by
dated amendment before real data is read.

The simulator is also unit-tested on hand-built days, as in
`tests/test_nq_mr.py`, before either run.

## Confirmation

Only setups that pass Q1, Q2 or Q3 in development go to the holdout. The
identical code runs **once** on 2025-04-01 → 2026-09-21. Confirmed if the same
statistic is > 0 with t ≥ 1.65 there.

If nothing passes in development, the holdout stays sealed, as it did for
`retest.md` and `selection.md`.

## What each outcome would mean

| Q1 | Q2 | reading |
|---|---|---|
| pass | pass | the setup works as taught, and the structure is why |
| pass | fail | the structure is a better place for the stop, but the trade still doesn't pay after costs |
| fail | pass | it pays, but any stop of that width would; the structure is not doing the work |
| fail | fail | closes the "the level's job is the stop" question for these four setups |

## Prior

**Weakly negative on Q2, open on Q1.** The direction edge these entries carry is
1–2 bp before costs, and a structural stop changes only which trades get
stopped, not the drift. But stop placement is a real claim that this project has
never tested cleanly, and E6b (stop below the level) was the least bad of the
pre-fix strategies.

## Amendment 1 — 2026-10-01, before any real data was read

**The random-walk check failed as first built, and the cause was the simulation,
not the design.** With each 5-minute bar built from five 1-minute steps, S − C in
the primary cell was +0.0037R for pullback (t 2.08) and +0.0024R for VWAP (t 1.67),
with several neighbouring cells beyond |t| 2. Both S and C also earned +0.05R to
+0.2R gross on a martingale, where the expected value is zero. The cause: on a path
that moves in coarse steps, price jumps past a stop but the simulator fills at the
stop, and the error relative to 1R is largest for the tightest stops.

**Fix to the check:** each simulated bar is built from 60 price steps
(`RW_SUB=60`, now the default; `RW_SUB=5` reproduces the failure). Liquid large caps
trade many times a minute, so this is closer to the real path. On 881,992
random-walk trades over 1,071 sessions, S − C is within 1.31 standard errors of
zero in all 24 cells, and **PASS** in every primary cell (ORB +0.55, level +0.72,
VWAP +0.70, pullback +0.93). Nothing in the design itself was changed.

**A second artifact the check exposed, which affects levels but not Q1.** With
tight stops, one 5-minute bar often reaches both the stop and the target, and the
rule counts the stop. On the random walk this costs the primary pullback cell about
−0.09R gross, for S and C alike. Because S and C share the width distribution, Q1
is unaffected; Q2 is biased against tight-stop setups. So, added as reporting, with
no change to any verdict:
- the share of trades whose exit bar reached both barriers (outcome code 3);
- Q2 with those trades credited the target instead, as an upper bound;
- the random-walk gross R of S for each setup and cell, as the level a setup
  would show with no edge at all.
