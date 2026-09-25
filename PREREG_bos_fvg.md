# Pre-registration: break-of-structure + FVG entry (E13)

Written before the code runs. The strategy as supplied:

> 1) Mark PMH/PML (or HOD/LOD). Wait for a strong break. MUST CLOSE beyond it.
> 2) Wait for an FVG to form, AFTER the breakout.
> 3) Enter ONLY when price taps into the FVG, and only on a confirming close.
> 4) Stop below the middle candle of the FVG. Target the next 1H high/low.
>    RR never below 1, ideal 1.5-3R.
> 5) 1-5m charts, 09:30-11:00 ET only, high-volume tickers, never during news.

## How each rule is operationalised

| rule | implementation | faithful? |
|---|---|---|
| PMH/PML | high/low of 04:00-09:30 | yes |
| strong break, must close beyond | 5-min **close** > PMH, first occurrence 09:30-11:00 | yes |
| FVG after the breakout | first 3-candle FVG (`high[i] < low[i+2]`) starting at or after the break bar | yes |
| tap into FVG | a later bar whose low enters the FVG band | yes |
| "respect / confirmation" | the tapping bar closes green AND closes back above the FVG low | **interpretation** |
| stop below middle candle | low of the FVG's middle candle, minus 1 tick | yes |
| target next 1H high | nearest swing high on 1-hour bars above entry, from the prior 2 sessions; no target found -> skip | **interpretation** |
| RR >= 1 | skip if (target-entry)/(entry-stop) < 1 | yes |
| 09:30-11:00 only | entries must occur in that window | yes |
| high-volume tickers | top 100 by trailing dollar volume | yes |
| never during news | **NOT IMPLEMENTED** -- no news calendar in this data | **no** |

Two rules are interpretations and one cannot be done at all. Results should be
read as "this strategy, mechanised" rather than "this trader's results".

## Statistic

Mean R per trade and t-stat, with R defined by the strategy's own stop and
target. Reported alongside: win rate, the realised RR distribution, and the
same trades run against the **random-entry control** from E10 on the same days.

## Decision thresholds

**WORKS** mean R > +0.10 with t > 3, and materially above the random control.
**DEAD** mean R <= 0.
**AMBIGUOUS** anything else.

## Prior

**Weakly negative.** Eleven intraday claims tested so far; one confirmed
(the open is volatile), the rest null or refuted, and E8 showed exit policy
cannot rescue a zero-edge entry. But this is the first fully specified
sequence -- break, then imbalance, then a tap with confirmation -- rather
than a single trigger, and conditioning on three events in order is a genuinely
different filter from anything in E1-E12.

## Hazards

- The confirmation rule is the discretionary part of a discretionary strategy.
  A negative result may be a verdict on my interpretation of "respect".
- No news filter, and the author says news matters. If the edge lives in
  post-news continuation, this test cannot find it.
- Twelfth test on overlapping data.
