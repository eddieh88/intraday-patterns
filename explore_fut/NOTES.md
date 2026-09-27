# Supply/demand zones on futures: development notes

Gold and four currency futures (GC, E6, B6, A6, J1), 5-minute data, 2021-01 to
2025-03. Prices are back-adjusted: levels differ from spot (for example, the
euro shows ~1.30 in June 2021), but distances and R-multiples are unaffected.
Timestamps are New York time.

## 1. Limit order at the zone (`structure.py`)

571 fills from 1,316 setups. R is net of 2 ticks.

| planned reward:risk | trades | target hit | break-even hit rate | mean R |
|---|---|---|---|---|
| under 2 | 65 | 38% | 39% | −0.11 |
| 2–3 | 109 | 28% | 28% | −0.11 |
| 3–5 | 177 | 24% | 21% | +0.02 |
| 5–8 | 128 | 25% | 14% | +0.60 |
| 8+ | 91 | 9% | 8% | −0.20 |
| all | 571 | 24% | | +0.08 ± 0.10 |

The hit rate tracks the break-even rate in every bucket, which is what no edge
looks like. Above 8:1 the zone is tiny compared with the move, and 91% of those
trades stop out. The 5–8 bucket was picked after seeing results, so it's a lead,
not a finding (tested on the holdout, `prereg/fut_zone_refined.md`).

## 2. The practitioner-review filters (`structure_fair.py`)

A reviewer of four sample charts said the backtest left out his filters. Their
list:
- a higher-timeframe trend
- a lower-timeframe trigger inside the zone
- a minimum zone width
- no news impulses
- a 3:1 minimum
- expiry at the weekend

Adding them:

| version | trades | mean R | hit vs break-even |
|---|---|---|---|
| 5-minute trigger inside the zone + weekend expiry | 262 | −0.07 ± 0.08 | 47% vs 46% |
| + 4-hour trend agrees | 142 | +0.02 ± 0.10 | 54% vs 49% |
| + 4-hour trend disagrees | 120 | −0.18 ± 0.12 | 39% vs 43% |
| + 3:1 minimum | 38 | −0.38 ± 0.30 | 13% vs 20% |
| all filters | 17 | −0.53 ± 0.39 | — |

**Confirmation and 1:3 are in conflict.** By the time the 5-minute trigger fires,
price has already bounced off the zone. With the stop still beyond the swing
extreme, the median planned reward:risk falls from 4.0 to 1.3. His published
process can produce both his entry and his reward:risk only if the stop moves up
to the small 5-minute swing after confirmation. That is the answer to "you didn't
trade his system", and it is the next test (`prereg/fut_zone_refined.md`).

Not implemented: "cancel on an opposite 1-hour break before the tap." The zone
sits where the impulse started, so a retrace to it must close back through the
impulse's own internal swings. The rule would cancel nearly every setup by
construction. A trend flip (a close beyond the protected level) still cancels.

The width and news filters removed only two trades each. The news calendar
covers FOMC and payrolls only.

## 3. Refined stop, with a random control, and the holdout

This was pre-registered in `prereg/fut_zone_refined.md`, which has the full
results. It **failed on both periods.**
- The zone trades lost 0.28R to 0.37R per trade more than random entries with
  the same stop and target.
- The 5–8 lead reversed on the holdout, to −0.54R.
