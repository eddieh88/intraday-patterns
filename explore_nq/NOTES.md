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
