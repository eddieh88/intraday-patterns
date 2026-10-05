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
