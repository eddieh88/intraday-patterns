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

## How each was approached

- **E1** descriptive only. No model, no trade simulation. Hard to get wrong,
  and correspondingly weak as evidence of anything tradeable.
- **E2-E5** event studies on a cached per-symbol-day table. Each is a single
  conditional mean or sign-agreement rate against an unconditional benchmark.
  No trade simulation, so no costs, no stops, no position sizing.
- **E6-E7** full trade simulation: entry, stop, exit, gap-through fills, 2bp
  costs. These are the only two that model execution.

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
8. **No intraday slippage model** beyond gap-through on stops. Market orders on
   news-driven names will do worse than modelled.
