# NQ intraday mean reversion

A long-only system posted on X by @MrMilkTrading. It runs on NQ 3-minute bars,
10:00–12:00 New York, and has four parts:
- a choppiness filter (efficiency ratio ≤ 0.35)
- a buy limit 1 ATR below the close
- a target at the middle of the signal candle
- a 1.5 ATR stop and a 15-minute time stop

We also tested the scale-in suggested in a reply. The rules, tests and full results
are in [`../prereg/nq_mean_reversion.md`](../prereg/nq_mean_reversion.md).

| file | |
|---|---|
| `mr.py` | Simulator and the registered tests. `python3 explore_nq/mr.py [holdout]` |
| `sensitivity.py` | Registered sensitivities and the exploratory other-day control |

Data: MarketParquet 1-minute NQ, back-adjusted, 2021-01 to 2026-09. He fills on
1-second data. With 1-minute bars we take the losing order inside a minute, and we
check that this does not decide the result (it doesn't; see the prereg).

## Result

| | development (2021-01 to 2025-03) | holdout (2025-04 to 2026-09) |
|---|---|---|
| as posted, net pts/trade | −0.72 (t −1.4) | +1.05 (t 0.8) |
| scale-in, net pts/trade | −0.66 (t −1.6) | +0.96 (t 0.9) |
| win rate, as posted / scale-in | 57% / 61% | 60% / 63% |

**Not profitable at a level we can tell from zero.** The positive holdout comes
from 2026 alone (+4.1 pts per trade, against −1.9 in April–December 2025), and 2026 is when the
rules were posted. He warned that the system is "likely very sensitive to regime
changes", and the year-by-year numbers agree: 2021 −0.16, 2022 −1.43, 2023 −0.21,
2024 −1.53, 2025 Q1 +0.70, 2025 Apr–Dec −1.91, 2026 +4.10.

The choppiness filter helps in the holdout (−0.37 without it, +1.05 with it) and not in
development (−0.49 without it, −0.72 with it).

## Taking it apart (exploratory, development only)

After the registered test failed, we changed one piece at a time to see what each
piece does (`tweaks.py` → `tweaks_dev.csv`). We also measured what price does after
a dip fill, with no exits in the way (`events.py`). About 40 variants were tried,
so a couple of |t| > 2 results would be expected by chance. Nothing here is a
finding.

**1. There is no bounce after the dip.** After a 1-ATR dip fills, NQ's mean move is
−0.01 to +0.00 ATR at every horizon from 1 to 60 minutes. That is the same as from
any minute of the window. Rips don't fade either. The same holds at 0.5 and 1.5
ATR. The choppiest readings (efficiency ratio < 0.2) are, if anything, the worst:
−0.036 ATR at 15 minutes.

**2. Before costs, the system makes exactly zero.** With no slippage and no
commission, the posted rules make +0.001 ATR per trade (t 0.08). Every variant of
the exits lands between −0.01 and −0.05 ATR. That is the cost of trading, and
nothing more.

**3. The win rate is geometry, not edge.** On a random walk, a bracket with the
target 1.0 ATR away and the stop 1.5 ATR away hits the target first
1.5 / 2.5 = 60% of the time. The posted system wins 57–58%; the time stop cuts some
winners. Moving the target moves the win rate and leaves the mean at zero:

| target | win rate | net ATR/trade |
|---|---|---|
| 0.5 ATR | 69% | −0.034 |
| middle of the candle (posted, ~1.0) | 57% | −0.031 |
| 2.0 ATR | 50% | −0.009 |
| none | 50% | −0.016 |

The scale-in's higher win rate works the same way. The average fill sits lower,
so the fixed target is closer.

**4. The other parts don't matter either.**
- The stop (0.75 ATR to none) changes nothing.
- A longer time stop is a little better, because fewer exits pay slippage.
- The choppiness filter doesn't pick reverting moments. Trending bars
  (efficiency ratio > 0.35) do the same.
- Shorts on rips are the same.
- Other windows are the same or worse. 9:30–10:00 is clearly worse (−0.14 ATR).
- ES, RTY and YM are worse (−0.08 to −0.12 ATR). Their ATRs are fewer ticks wide,
  so fixed costs weigh more.

**5. 2026 is not unusual.** The quarterly average of the 15-minute move after a dip
swings between about −0.2 and +0.2 ATR, with a standard error of about 0.1 per
quarter.

| stretch | quarterly average |
|---|---|
| 2026 Q1–Q3 | +0.08, +0.15, +0.05 |
| 2024 Q1 | +0.21 |
| 2025 Q1–Q2 | +0.155, +0.149 |

Earlier good stretches were followed by bad ones: 2024 Q3 −0.21, 2025 Q4 −0.16.
NQ's ATR is also the highest in 2026 (a median of 39 points, against 19–34 before).
That makes fixed tick costs a smaller share of each trade.

**What the system actually is:** a bracket order on a random walk. The target sits
closer than the stop, so the win rate is high, and the average is minus the costs.
Stretches of mild post-dip reversion, like 2026, make it look good for a few months.

## Does it work in sideways ("crab") markets? (`regime.py`, exploratory)

**In hindsight, yes.** Mornings are cut into fifths by how sideways the
10:00–12:00 window turned out:
- The four most sideways fifths make +0.03 to +0.07 ATR per trade, net.
- The most trending fifth loses −0.25 ATR per trade, and that wipes out the rest.

This is biased in the strategy's favour: a window that ends flat is one where the
dips came back.

**In advance, no.** None of these, cut into fifths, picks those mornings:
- the daily efficiency ratio over 10 or 20 sessions
- daily ADX(14)
- the efficiency ratio of the session so far

Their fifths bounce between −0.10 and +0.06 ATR with no order, and the standard
error per fifth is about ±0.04. The most sideways fifth by the 10-day ratio or ADX
nets +0.01. This is the same wall `selection/` hit: nothing visible in the morning
says which mornings will trend.
