# Pre-registration: the "silent flip"

Written before any code for this study exists. Nothing below is revised after
seeing results; changes are dated amendments made before the data they concern
is read.

## Source

A YouTube video by a trader called Carl ("the silent flip strategy"), shown with
one live trade (Uber, short from the flip high, about 3–4R, with the stop moved
three times). It is pitched as one chart, one 15-minute time frame, and four
lines. The video also promotes a paid copy-trading service and says the setup
appears about weekly per stock.

## The claim

> Yesterday's high and low, and the next swing beyond each, are where large
> sellers and buyers sit. In the first hour, a strong opening candle that runs
> into one of these levels, followed by a candle in the opposite direction that
> does not break the level, marks a reversal. Fade it, with the stop beyond the
> pattern and the target at the opposite side of yesterday's range.

## What has already been seen

Related ideas have lost here before: fading opening-range breaks (E4), fading a
pre-market sweep of yesterday's high or low (E5), and prior-day levels holding
on a retest no more often than fake levels (`retest.md`, 50.2% vs 50.3%). None of
those had this two-candle confirmation, the flip levels, or the far target. The
holdout below was read on 2026-10-01 for `structure_stops.md`, with different
entries; it has never been read for this rule.

## Data

- **Universe:** each day's top 100 from `cache/intraday_pool.parquet` (point-in-time).
- **Development:** 2021-01-19 → 2025-03-31. **Holdout:** 2025-04-01 → 2026-09-21,
  sealed by `lib/holdout.py`, read once under *Confirmation*.
- **Bars:** 15-minute RTH bars built from the 5-minute bars (09:30, 09:45, …),
  half-day aware. Execution is simulated on the 5-minute bars.
- **ATR15:** mean high − low of the prior 14 RTH 15-minute bars, carried across
  sessions. Known at 09:30.

## Levels (all known before 09:30)

| level | definition |
|---|---|
| range high RH | yesterday's RTH high |
| range low RL | yesterday's RTH low |
| flip high FH | the most recent 15-minute **swing high** from a session before yesterday whose high is above RH, searching back at most 20 sessions. A swing high is a bar whose high exceeds the highs of the 2 bars on each side (bars from adjacent sessions count as neighbours). If none, there is no FH that day |
| flip low FL | the mirror: the most recent swing low before yesterday below RL |

## The trade (short side; the long side mirrors it at RL and FL)

1. **Candle 1** = the 09:30–09:45 15-minute bar. **Strong and bullish:**
   - close > open
   - range ≥ **1.0 × ATR15**
   - body ≥ **0.6 × range**
2. **Tests an upper level.** L is the higher of RH and FH that candle 1 reached to
   within **0.25 × ATR15** (high ≥ L − 0.25 × ATR15). Candle 1 must close below L.
   If it reached neither, no trade.
3. **Candle 2** = the 09:45–10:00 bar, the "silent" candle:
   - closes red (close < open)
   - closes below L
   - does not trade more than 0.1 × ATR15 above both L and candle 1's high
4. **Entry:** a sell-stop at candle 2's low, live on the 5-minute bars stamped
   10:00–10:25 (the first hour). It fills at the low, or at the bar's open if
   the bar opens below it. It is cancelled if price trades at or above the stop
   first.
5. **Stop:** the higher of candle 1's and candle 2's highs, + 0.1 × ATR15.
6. **Target:** RL, yesterday's low (the opposite range level, as in his live
   trade). No trade if RL is not below the entry.
7. **Exit:** stop, target, or the session's last 5-minute bar.
   - In the fill bar, the stop counts if that bar's high reached it, and the
     target is not credited.
   - Later bars: stop checked first, and gaps fill at the open.
8. **Cost:** 3 bp round trip, in R. 1 bp and 6 bp are reported.

One trade per name per day at most (candle 1 is one bar). His stop trailing is a
reported variant, not the rule.

## Controls

**Fake levels (do the levels matter?).** The whole rule runs again on the same
name-day with fake levels: RH, RL, FH and FL taken from a random session of the
same name within the prior 20 (excluding yesterday), each expressed as a ratio
to that session's 09:30 open and re-applied to today's 09:30 open (seed 7). They
sit at the distances levels typically sit, but they are not this day's levels.

**Random entry (does the pattern time anything?).** For each real trade, 20
entries in the same name, day and side, at the open of a random 5-minute bar
stamped 10:00–10:25. Each uses the real trade's stop and target distances in
price, the same exits and the same costs (seed 7). The control is the mean of
the 20.

## Tests

Net R at 3 bp, session-clustered standard errors.

- **Q1, pays:** mean net R of real trades > 0.
- **Q2, the levels matter:** real minus fake-level net R > 0. The two samples are
  unpaired, and the standard error clusters both by session.
- **Q3, the timing matters:** real minus random-entry net R > 0, paired per trade.

A question **passes in development** only if all of these hold:
1. t ≥ 2.0 in the primary specification above.
2. Positive in at least 3 of the 4 blocks: 2021, 2022, 2023, and 2024 with 2025 Q1.
3. Positive in at least 2/3 of the robustness grid (81 cells, below).

**Robustness grid** (development only, reported in full):
- candle-1 range: 0.75, 1.0, 1.5 × ATR15
- body share: 0.5, 0.6, 0.7
- test tolerance: 0.1, 0.25, 0.5 × ATR15
- target: RL; the nearer range level on the way (RH when shorting from FH,
  otherwise RL); a fixed 2R

**Also reported, no verdict:**
- trade counts per year, and setups per stock per month (he says about weekly)
- win rate and the exit mix
- R from RH tests and FH tests separately
- long and short separately
- the entry window extended to 11:00
- his trailing stop: break-even once the trade is +1R, then the stop trails the
  last completed 15-minute high/low
- gross, 1 bp and 6 bp results

## Random-walk check, before any real data

The pipeline runs first on simulated random-walk names: 100 names, the same
number of sessions as development, and 60 price steps per 5-minute bar (as in
`structure_stops.md`, Amendment 1). There, levels mean nothing. Both Q2
(real − fake) and Q3 (real − random entry) must be within 2 standard errors of
zero in the primary specification. Otherwise the design has a mechanical bias
and is fixed by dated amendment. The simulator is unit-tested on hand-built days
first.

## Confirmation

Any question that passes in development is run **once** on the holdout with the
primary specification. Confirmed if it is > 0 with t ≥ 1.65. If none passes,
the holdout stays sealed for this rule.

## Prior

**Negative.** Every first-hour fade and every prior-day level test here has
failed, and the open leans slightly toward continuation. Two things are new:
the confirmation candle, and a target several R away, which can pay with a low
win rate. Expect a few thousand trades in development, enough to see an edge of
about 0.1R per trade.

## Amendment 1 — 2026-10-05, before any code or data

**The scan.** He watches several stocks each morning and trades whichever one forms
the pattern. The primary test already scans the day's top 100 and takes every
setup, so its mean net R per trade is the scan's per-trade result. Added as
reported, no verdict: **one trade per day across the universe**, the setup whose
entry fills first. Ties at the same 5-minute bar are broken at random (seed 7).
For it, the report gives the number of trading days with a trade, mean net R
per day, its t, and the share of days positive.

## Amendment 2 — 2026-10-05, before any real data was read

**The random-walk check, as registered (100 names), passes:** Q2 real − fake
+0.024 ± 0.103 (t 0.23), Q3 real − random +0.020 ± 0.035 (t 0.56), on 541 real
trades. At that size it cannot see a bias under about 0.4R, so it was also run
at 1,000 names (three seeds) and 500 names (four seeds):

| run | trades | Q2 real − fake | Q3 real − random |
|---|---|---|---|
| 1,000 names, seed 13 | 5,385 | +0.077 (t 2.37) | −0.021 (t −1.73) |
| 1,000, seed 21 | ~5,300 | −0.067 (t −1.96) | −0.032 (t −2.75) |
| 1,000, seed 34 | ~5,300 | −0.022 (t −0.70) | −0.039 (t −3.14) |
| 500, seed 41 | 2,791 | −0.045 (t −1.04) | −0.050 (t −3.22) |
| 500, seed 52 | 2,768 | +0.068 (t 1.41) | −0.013 (t −0.75) |
| 500, seed 63 | 2,742 | −0.016 (t −0.33) | −0.066 (t −3.84) |
| 500, seed 74 | 2,760 | −0.007 (t −0.16) | −0.076 (t −4.59) |

**Q2 has no bias, but its standard error is too small.** The seven estimates
average about zero, on both sides. Their t values have variance 1.88 rather than
1 (χ² 13.2 on 7 df, p ≈ 0.07). The first seed's failure was chance. Real and fake
trades in this test come from the same paths and rest on heavy-tailed outcomes
with targets near 3.5R; the clustered standard error evidently understates the
spread. **Change: Q2's critical t in development rises from 2.0 to 2.75**
(2.0 × √1.88). The holdout's rises from 1.65 to 2.26.

**Q3 is biased against the setup by about −0.04R.** All seven estimates are
negative. The cause is the registered conservative rule: when the bar that
fills the stop order also reaches the stop, it counts as a loss, though the stop
may have traded before the fill. The random control enters at a bar's open and
never meets that ambiguity. The bias makes Q3 harder to pass, so the rule is
kept. Q3 is also reported with +0.04R added back, without a verdict.

**Q1 reference.** On the random walk the primary rule averages +0.02R to +0.07R
gross and −0.03R to +0.02R net at 3 bp. This is the level a setup shows with no
edge, and it is reported next to Q1.

Nothing else changes. The flip simulator was also fixed to use its own copy of
the 60-step walk: loading `stops/random_walk_check.py` put `stops/` first on the
worker path, so workers imported the wrong `sim` and died, and the first run
hung.

## Results — development, 2026-10-05

`python3 flip/run.py && python3 flip/analyze.py`. Primary specification: **877
real trades** on 557 sessions across 196 names, and 915 fake-level trades. Net R
at 3 bp, session-clustered.

| question | estimate | t | years positive | grid positive | verdict |
|---|---|---|---|---|---|
| Q1 pays | −0.037 ± 0.037 | −1.00 | 1/4 | 0/81 | **fail** |
| Q2 levels matter (real − fake) | −0.002 ± 0.049 | −0.03 | 2/4 | 25/81 | **fail** |
| Q3 timing (real − random entry) | −0.051 ± 0.018 | −2.78 | 0/4 | 3/81 | **fail** (bias-corrected −0.011, t −0.59) |

**Nothing passes, so the holdout stays sealed for this rule.**

- **Before costs it is zero:** +0.003R gross. Net is −0.011R at 1 bp, −0.037R at
  3 bp, and −0.077R at 6 bp.
- **Exits:** 21% of trades reach the target (median 1.9R away), 41% are stopped,
  and 38% are still open at the close.
- **By level:** RL +0.039, RH −0.040, FH −0.079, FL −0.077. None differs from zero,
  and the flip levels, the part the method adds, do worst.
- **Variants:** his trailing stop −0.034. Entry window to 11:00 −0.037.
- **One trade a day across the universe (his scan):** 557 days, −0.046R a day
  (t −1.01), 44.9% of days positive.
- **Fake levels:** they set up as often (915 vs 877 trades) and earn the same. On
  these stocks, yesterday's high and low and the next swing beyond do not mark
  where reversals happen.
- **Frequency:** 0.09 setups per name per month, about one a year per stock in
  the top 100. He says about weekly; his reading of "strong" and "tests" is
  presumably looser than these rules.

**A weakness found in reading the grid, not in the verdict.** The candle-1
strength threshold (0.75, 1.0, 1.5 × ATR15) barely changes the trades, because
ATR15 comes from yesterday's last 14 bars. Those are afternoon bars, and the
09:30 bar is usually several times their size, so almost every opening candle
counts as "strong". The body-share rule is the filter that binds. A stricter
definition, such as against the average 09:30 bar of the last 20 sessions,
would select fewer and bigger candles. It was not tested, and it would be a new
specification, not a rescue of this one.
