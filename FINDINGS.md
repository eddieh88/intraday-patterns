# Intraday experiments E1-E18 — what was claimed, how it was measured

Data: MarketParquet `stock_5min`, 2021-01-04 .. 2026-09-21, 1,462 sessions,
04:00-20:00 ET. Derived tables in `cache/`.

**Read the limitations section before the results.**

| # | claim tested | source of claim | measurement | universe | n | result |
|---|---|---|---|---|---|---|
| E1 | the open differs from the rest of the day | practitioner consensus | median 5-min bar range and volume share, by 30-min block | top 300 by $vol, 78 sampled days | 78 days | **CONFIRMED** 2.94x midday range; 35% of volume in 23% of hours |
| E2 | opening gaps fill the same session | "gaps always fill" | % of gap days where price trades back through prior close | top 200 | 275,399 | **SIZE-DEPENDENT** 69% for <0.2% gaps, 27% for >2% |
| E3 | the opening move is a false move that reverses | ICT "PO3 / judas swing" | sign agreement between 9:30-10:00 and 10:00-11:00 | top 200 | 274,142 | **NULL** 50.5% reversal vs 50% chance |
| E4 | the opening range is swept then reverses | ICT liquidity-sweep | % of OR breaks that close back inside; fade vs hold return | top 200 | 113,513 | **REFUTED** breaks continue; fading loses 5.7bp, t=-9.3 |
| E5 | pre-market determines the day's direction | "session script" post | corr(04:00-09:30 move, 9:30-11:00 move); sweep-and-reverse rule | top 200 | 261,143 | **REFUTED** 49.2% same-direction; sweep rule loses, t=-6.1 |
| E6 | prior-day S/R break + retest pays in the open | break-and-retest diagrams | R-multiple, stop below entry bar (a) and below level (b) | top 100 | 86,170 / 59,668 | **NEGATIVE** -0.099R then -0.073R, t=-8.3 |
| E7 | ORB on high-relative-volume names | Zarattini-Barbon-Aziz (2024) | R-multiple, 2 stop variants, by relvol rank tier | top 1000 filtered, 2,392 names | 211,741 | **DEAD by prereg** +0.009R t=1.25; filter sorts monotonically |
| E8 | the EXIT rule decides it, not the entry | user — "not all people hold til 3R or perish" | 7 exit policies on IDENTICAL entries | top 100 | 35,232 | **REFUTED** all seven lose, -0.063R to -0.101R |
| E9 | (descriptive) what does the trade do after entry? | — | MFE / MAE / bars-to-peak / bars-to-stop | top 100 | running | — |

## How each was approached

- **E1** descriptive only. No model, no trade simulation. Hard to get wrong,
  and correspondingly weak as evidence of anything tradeable.
- **E2-E5** event studies on a cached per-symbol-day table. Each is a single
  conditional mean or sign-agreement rate against an unconditional benchmark.
  No trade simulation, so no costs, no stops, no position sizing.
- **E6-E8** full trade simulation: entry, stop, exit, gap-through fills, 2bp
  costs. The only ones that model execution.
- **E8** holds entries fixed and varies only the exit, so the two are separated
  rather than confounded. Its result -- a 0.04R spread across seven very
  different policies, all negative -- is why the remaining question is about
  the entry, not the exit.
- **E9** is descriptive, not a strategy test. It constrains which exits could
  possibly work, rather than selecting one after the fact.

## CORRECTION — the universal -0.1R was a measurement artifact

Every trade-simulating experiment (E6-E13) returned a mean between -0.07R and
-0.14R regardless of entry, exit, or filtering. That convergence is evidence
about the measurement, not thirteen independent verdicts. Decomposition, on
138,930 random-entry trades:

| stop width | risk% | ideal/0bp | ideal/2bp | gap/0bp | gap/2bp |
|---|---|---|---|---|---|
| 0.5 bar | 0.18% | **+0.014** | -0.121 | +0.012 | -0.123 |
| 1 bar | 0.36% | **+0.018** | -0.050 | +0.017 | -0.051 |
| 2 bars | 0.72% | **+0.013** | -0.021 | +0.012 | -0.022 |

- **Gross is slightly POSITIVE everywhere** (+0.013 to +0.018R). The bracket is
  not broken; that number is equity drift.
- **Slippage is negligible** -- gap-through fills cost 0.002R.
- **Costs are the whole story, and scale inversely with stop width.** The same
  2bp is -0.135R at a half-bar stop and -0.034R at a two-bar stop.

I used stops of roughly half a bar range throughout, which turned a 2bp
round trip into 11% of the risk unit. Every experiment then measured the same
friction, which is why they all landed in the same band.

**What this does not change:** gross edge is ~+0.015R everywhere, i.e. drift,
not signal. The *relative* comparisons in E8 and E10 were computed on identical
footings and stand. **What it does change:** the absolute figures reported for
E6-E13, and the framing "every strategy loses 0.1R", which was wrong. The
correct framing is "no strategy has gross edge, and the cost model then
subtracted a constant that depended on my stop width."

## E10b — the corrected entry comparison

2-bar stop, 1bp round trip, friction ~-0.017R instead of -0.135R:

| entry | n | mean R | vs random | t(diff) | p |
|---|---|---|---|---|---|
| **random** | 139,740 | **-0.002** (t=-0.51) | — | — | — |
| level retest | 35,232 | -0.005 | -0.003 | -0.38 | 0.706 |
| ORB | 53,880 | +0.005 | +0.007 | +1.10 | 0.270 |
| VWAP reclaim | 100,920 | +0.006 | +0.008 | +1.58 | 0.113 |
| pullback | 93,417 | +0.010 | +0.011 | +2.08 | 0.037 |

Bonferroni threshold for 4 comparisons: p < 0.0125.

**Random entry is exactly zero**, which validates the simulation -- a random
bracket on a near-efficient series should earn nothing, and it does. No entry
beats it: the best, `pullback`, fails Bonferroni and is +0.011R regardless.
The chart-pattern entry (`level retest`) is *worse* than random.

This supersedes E10 and is the definitive result of the intraday series.

## E10c — the definitive result: symmetric long/short

E10b was **long-only**, so its slightly positive gross was market drift leaking
in, not entry quality. Giving every entry a short form makes drift cancel in
the long-minus-short spread.

| entry | n long | long R | n short | short R | L-S spread | excess over drift | p |
|---|---|---|---|---|---|---|---|
| **random** | 121,515 | -0.003 | 121,511 | -0.023 | **+0.0195** (t=3.63) | — (this IS the drift) | — |
| ORB | 46,683 | +0.010 | 46,006 | -0.010 | +0.0202 | +0.0007 | 0.938 |
| level | 28,727 | -0.001 | 29,303 | -0.023 | +0.0219 | +0.0024 | 0.834 |
| VWAP | 87,669 | +0.009 | 87,682 | -0.016 | +0.0254 | +0.0059 | 0.451 |
| pullback | 82,812 | +0.011 | 82,104 | -0.015 | +0.0260 | +0.0065 | 0.425 |

**CORRECTION.** E10c first reported "+0.0195R, t=3.63" as a measured drift
baseline. That t-stat treated 243,026 trades as independent. They are not:
~174 trades share each session's market-wide move, so the effective sample is
closer to the ~1,400 sessions than to the trade count.

A dated re-run gives a weighted mean spread of **-0.0140R** -- the opposite
sign -- with a year-to-year standard deviation of 0.070R:

| year | universe ret/day | L-S spread |
|---|---|---|
| 2021 | -0.137% | -0.013 |
| 2022 | +0.074% | -0.056 |
| 2023 | +0.116% | +0.110 |
| 2024 | +0.005% | -0.002 |
| 2025 | -0.071% | -0.098 |
| 2026 | +0.058% | -0.024 |

t on the six yearly observations: **-0.48**. Correlation with that year's market
return +0.498, p=0.315. With within-day correlation of only rho=0.05 the
variance inflation factor is 9.6 and the original t of 3.63 becomes 1.17.

**There is no significant drift effect.** The correct statement is: *random
entry is indistinguishable from zero, and no structured entry is
distinguishable from random.* The excess-over-random p-values (0.42-0.94) were
already non-significant and clustering only moves them further from
significance, so that conclusion is unaffected -- both arms share the same
days, so the correlation largely cancels in the difference.

In E10b the same `pullback` arm looked like +0.010R at t=2.31 and needed a
Bonferroni correction to dismiss. That apparent edge was drift entering through
a long-only design.

**This supersedes E10 and E10b.** Intraday entries carry no directional
information beyond market drift.

## E10e — TWO ERRORS CORRECTED, and the ordering flips

A practitioner review found two errors in E10c/E10d.

**Error A: the wrong column was read as the edge.** With edge `e` and drift `d`,
a mirrored pair gives `long ~ e+d` and `short ~ e-d`. So:

    L - S  ~ 2d      cancels the EDGE, measures the DRIFT
   (L + S)/2 ~ e     cancels the DRIFT, measures the EDGE

E10c/E10d reported **L-S** as the edge statistic. It is the drift statistic. The
symmetric design was built to isolate drift and then the drift column was read
as though it were signal.

**Error B: the universe was not point-in-time.** Names were ranked on dollar
volume summed over the whole 2021-2026 period, which selects the ones that
became heavily traded *because they ran* — the same bug as Step 9's 19pp/yr
leak. Now: trailing 20-session dollar volume, known before each session, giving
200 distinct names across 1,425 sessions rather than 100 fixed.

| entry | long R | short R | **(L+S)/2 = edge** | clustered t | excess over random | t |
|---|---|---|---|---|---|---|
| pullback | +0.008 | -0.008 | **+0.0001** | +0.01 | +0.0128 | +1.94 |
| VWAP | +0.009 | -0.013 | **-0.0018** | -0.39 | +0.0109 | +1.90 |
| ORB | +0.005 | -0.009 | **-0.0019** | -0.21 | +0.0108 | +1.10 |
| level | +0.005 | -0.021 | **-0.0085** | -1.08 | +0.0042 | +0.50 |
| **random** | -0.003 | -0.022 | **-0.0127** | -3.82 | baseline | — |

ICC estimated from the data: **0.0090** over 1,425 session clusters.
**Minimum detectable edge at 80% power: ~0.0132R.**

**All four entries beat random**, reversing the earlier conclusion. But:

1. **Nothing is significant** — best is t=1.94.
2. **The study is underpowered for these effect sizes.** MDE 0.0132R against a
   largest observed excess of 0.0128R. A small real edge and noise are not
   separable here. The earlier "p > 0.42, nothing beats random" reported a null
   without establishing what a null could mean.
3. **Random's -0.0127R is the cost drag.** 1bp on a 0.72% risk unit is 1.4% of
   R = -0.014R. Entries beating random by ~0.012 therefore land at **zero**,
   not positive — they recover the cost and no more. At a realistic 3-6bp
   all-in the drag is -0.042 to -0.084R and none of them approach it.

**The conclusion is no longer "entries carry no information."** It is: *any edge
present is below our detection threshold and below realistic costs.*

**Supersedes E10, E10b, E10c and E10d.**

## E15-E18 — the estimand problem, and the benchmark that closed it

E10e left a long-short spread that reviewers correctly said was not an edge.
Four experiments were needed to get to a statistic that means what we wanted.

### The estimand

`L - S = 2d` measures DRIFT.  `(L + S)/2 = e` measures EDGE.  Every number
before E16 reported the first while describing the second.

Worse, both natural weightings of "signal vs random" are biased, in opposite
directions, by `n` = signals per side per session — which is not known until
11:00 and so is not a tradable weight either way:

```
estimand                     excess    bias
trade-weighted vs random     +0.011    UP    over-weights the majority side,
                                             which is the side the day rewarded
                                             (corr(tilt, move) = +0.351, p=2e-42)
side-balanced vs random      -0.012    DOWN  gives the minority side equal
                                             weight; on a trend day those are
                                             counter-trend signals that lose
```

### E16 / E16b — matched placebo

Each signal is paired with a random bar in the **same name, session, side, time
neighbourhood** (E16b adds: **same risk unit**), drawn **at or after** the
signal.  Equal weight per pair, so `n` cancels.

The after-only rule is error 09: placebos drawn up to 12 bars *before* the
signal enter ahead of the breakout and capture the move that defines it.  Those
earn **+0.67R** against the signal's -0.08R.

Because the placebo inherits the side, the paired difference holds direction
fixed — it measures **timing**, not direction.

### E17 — direction and timing separated

Direction needs the signal's **absolute gross R**, since a random-side entry has
zero expected gross R.  479,659 matched pairs, gross:

```
                DIRECTION                TIMING (signal - delayed same side)
entry          abs gross R      t        diff       t         n
pullback           +0.0213   +2.73     +0.0098   +1.91   252,952
ORB                +0.0198   +1.53     +0.0006   +0.08    46,818
VWAP               +0.0152   +2.15     -0.0019   -0.48   151,616
level              +0.0075   +0.68     +0.0076   +1.09    28,273
```

Direction is positive; **timing adds nothing**.  Four entries tested, so at
Bonferroni alpha = 0.05/4 the critical |t| is 2.50: **pullback clears it, VWAP
does not.**

Stop-first and target-first tie-breaks give identical results to four decimals.
`diagnostics/barrier_span_count.py` explains why: **35 of 639,329** resolved
trades have one bar containing both barriers, 0.005%.

### E18 — the momentum benchmark (the decisive result)

Same bar, same stop, same 3R target — but side = **sign of the past k bars**.
No level, no break, no retest.  If the pattern does work, it must beat this.

```
entry      pattern   mom k=3   mom k=6   mom k=12   pattern-mom6       t
pullback   +0.0210   +0.0095   +0.0183   +0.0214        +0.0057   +0.90
ORB        +0.0198   +0.0198   +0.0198   +0.0346        +0.0000     n/a
VWAP       +0.0148   +0.0127   +0.0215   +0.0183        -0.0029   -0.59
level      +0.0086   +0.0060   +0.0084   +0.0278        +0.0040   +0.33
```

**No entry beats it.**  The 1-2bp is generic opening continuation, not anything
specific to the pattern.

**ORB's zero is exact and its t is undefined** because the difference is
identically zero on every trade: an upward opening-range break *is* a positive
sign of the recent move, so the momentum rule selects the same side every time.
**ORB is a momentum rule with a level drawn on top of it.**

### The ORB reconciliation — first hypothesis was wrong

Two internal ORB numbers disagreed in sign: -0.0700 and +0.0198.

E18(a) hypothesised candidate-count weighting.  **That was refuted by its own
test**: the reweighting moves ORB by 0.005R and corr(n candidates, signal R) is
-0.014.  `diagnostics/orb_reconcile.py` found the real cause by toggling each
difference one at a time:

```
long only, 1bp cost, every 10th session    -0.0683
+ drop the cost charge                     -0.0534   (+0.015)
+ include the downside break, not just up  +0.0441   (+0.098)  <- the gap
+ every 2nd session, not every 10th        +0.0173   (-0.027)  within noise
```

The diagnostic traded **long breaks only**, net of 1bp, on a tenth of the
sample.  Almost the whole sign flip is the missing short side.

`diagnostics/orb_clustered_se.py`, SEs clustered by session (713 sessions):

```
arm                       R    clust SE       t          n
long only  @0bp     +0.0142      0.0214   +0.66     27,000
short only @0bp     +0.0202      0.0250   +0.81     27,324
both sides @0bp     +0.0172      0.0136   +1.26     54,324
both sides @1bp     +0.0029      0.0136   +0.21     54,324
```

**ORB was never significant in either direction.**  The two numbers disagreed by
0.09 on a quantity whose standard error is 0.014-0.021.  A diagnostic must carry
its own specification with it or it cannot be compared to anything.

### Selection does not rescue it

Relvol split under the matched-placebo design, **pooling all four entries**:

```
condition              n    direction R        t      timing        t
relvol < 1.5x    416,921        +0.0173    +2.30     +0.0044    +1.08
relvol 1.5-3x     50,411        +0.0295    +2.44     +0.0112    +1.45
relvol > 3x       12,327        +0.0103    +0.51     +0.0014    +0.10
```

Not monotonic — middle tier highest, top tier weakest on the thinnest sample.
The two earlier claims about this split, **+0.0688** (helps) and **-0.0637**
(hurts), were both artifacts of the biased estimand.  This proxy carries no
ordering.

**Supersedes E10e for the entry-comparison claim.**

## Correction — the universe used future volume

Found 2026-09-25, while preparing a selection model that would have made it fatal.

### What was wrong

`build_daily.py` chose its 200 candidate names by dollar volume **summed over all
of 2021–2026**. The E10e fix made the daily top-100 point-in-time *within* that
pool, but the pool itself was picked with hindsight: a stock that only became
heavily traded in 2024 was already a candidate in 2021, because of what it did
later. It is error 01 one level up.

Two further data faults surfaced while fixing it:

- **Holiday files.** The vendor writes a file for each US market holiday holding
  a handful of symbols. 27 of them were being read as sessions.
- **Ticker reuse.** Every script stripped the `-DELISTED` suffix. Where a dead
  company's ticker was reused, that merged two companies into one price series —
  on the same day, for FISV. The suffix is now kept; it identifies the company.

### The fix, and the test that guards it

Each day's pool is now ranked on the mean RTH dollar volume of the **prior 20
market sessions** only, holidays dropped, suffix kept. `cache/intraday_pool.parquet`
records who was eligible each day, and E17/E18 read their top-100 from it, so the
rule lives in one place.

`data/universe_check.py` rebuilds the pool independently, from raw files
truncated at the day before, on six dates, and requires an exact match: 150/150
on all six. It also requires early pools to contain later-delisted names (18 of
230 in the first 90 days: ATVI, BBBY, CCIV, DISCA…).

### How wrong the old pool was

| | |
|---|---|
| overlap, old daily top-100 vs true daily top-100 | **90.6%** mean; 85.8% first year; 73% worst day |
| names in a true daily top-100 at some point | **439**, against the old pool's 200 |
| old candidates first eligible a year or more in | **34** of 200 — APP, ANET, DELL, BE, CMG… |

### Rerun on the corrected universe

E17 — direction, gross, stop-first:

| entry | old pool | corrected | t |
|---|---|---|---|
| pullback | +0.0213 | **+0.0228** | +2.96 |
| ORB | +0.0198 | +0.0177 | +1.36 |
| VWAP | +0.0152 | +0.0160 | +2.27 |
| level | +0.0075 | +0.0077 | +0.69 |

Timing is still zero on all four (pullback closest, t = 1.87). Relative volume
still carries no ordering. Only pullback clears Bonferroni's 2.50.

E18 — setup vs momentum (k=6), **on the same trades** (those with six prior
bars), 1,435 sessions of which every second is used:

| entry | n | setup, next open | momentum, next open | **diff** | t | diff, signal close | t |
|---|---|---|---|---|---|---|---|
| pullback | 190,584 | +0.0249 | +0.0189 | **+0.0060** | +0.93 | +0.0071 | +1.10 |
| ORB | 48,771 | +0.0188 | +0.0188 | **0.0000** | — | 0.0000 | — |
| VWAP | 121,664 | +0.0210 | +0.0207 | **+0.0003** | +0.07 | −0.0009 | −0.19 |
| level | 21,983 | +0.0129 | +0.0077 | **+0.0052** | +0.45 | +0.0031 | +0.27 |

**Every conclusion holds.** Every figure moved by less than 0.003R. And the
next-bar fill, which is the tradeable one, does not cost the edge — the concern
that it lived in the first bar after the signal is not borne out.

The paired table replaces an earlier one whose columns did not subtract: the
difference was paired on trades with six prior bars, while each column averaged
over all trades.

**Not rerun:** E1–E13. They are marked pre-fix, and E2–E5 report percentages
rather than R, but they were measured on the hindsight pool.

## Limitations — all of them

1. **Only E7 was pre-registered.** E1-E6 had thresholds chosen while looking at
   the data. That is exactly the practice that produced a retracted +0.37 in
   this project's earlier equity work.
2. **Inconsistent universes.** E1 used 300 names on 78 sampled days; E2-E5 used
   200; E6 used 100; E7 used 2,392. Results are not comparable across rows.
3. **No holdout.** Every number is in-sample over the same 2021-2026 window.
4. **No multiple-testing correction** across seven experiments.
5. **E6 was re-specified once** (stop moved from entry-bar to level) after the
   first version failed. The second run is therefore exploratory, not
   confirmatory.
6. **Spread is assumed, not measured.** 2bp round trip. Corwin-Schultz on
   5-minute bars gave 7.8bp flat across all liquidity tiers, which is clearly
   measuring noise rather than spread. Without quote data the true cost is
   unknown, and it is the number that decides E6 and E7.
7. **Period is 2021-2026 only.** E7's source paper covers 2016-2023; the
   overlap is three years and gives exactly zero.
8. **No intraday slippage model** beyond gap-through on stops -- though the
   decomposition shows this is worth only 0.002R, so it was never the issue.
9. **Stops were too tight in E6-E13** (~0.5 bar range), which is the source of
   the -0.1R artifact above. E10b re-runs the entry comparison at a 2-bar stop
   and 1bp cost.
10. **Indexes and futures were absent.** E1-E13 ran on single stocks: the top
   100 by dollar volume contains 99 stocks and one ETF. The strategies being
   tested are overwhelmingly taught on ES/NQ/SPY. `etf_5min` and `futures_5min`
   have since been downloaded (3.2 GB and 511 MB); ES was verified
   back-adjusted, with large overnight gaps no more concentrated in roll
   windows than chance (25 observed vs 21 expected).
11. **The entry rule was the wrong object.** E18 shows no entry beats a naive
   momentum rule at the same bar. If the level's job is to set the RISK UNIT
   rather than the direction, every test in this log aims at the wrong target.
   Untested.
12. **Bonferroni over four entries** is applied in E17; E1-E13 still carry no
   multiple-testing correction, and the forking-paths count across the whole
   series is far larger than four.
13. **No news calendar.** One tested strategy says explicitly: never trade
   during news, only after. We cannot filter on that at all.
14. **E1–E13 used a hindsight-selected universe** (see the correction above).
   E17 and E18 were rerun on the point-in-time universe and did not change; the
   earlier experiments were not.
