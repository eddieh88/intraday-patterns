# Intraday experiments E1-E7 — what was claimed, how it was measured

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
