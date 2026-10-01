# Our own FX strategy: development (2021-2026 spot bid/ask)

Data: HistData spot quotes for 8 pairs, reduced to 1-minute bid/ask bars
(`data/histdata_fetch.py`, `data.py`). Trades fill at the ask when buying and at the
bid when selling, so the spread is paid for real. 2010–2020 is sealed for the final
test.

## Spreads (median pips by New York hour, 2021–2026)

Overnight, spreads are nearly as tight as in the day. The 17:00 rollover is 4–9×
normal, and 18:00 is still wide.

| pair | 17:00 | 18:00 | 20:00–02:00 | daytime |
|---|---|---|---|---|
| EURUSD | 1.95 | 0.47 | 0.29–0.33 | 0.27–0.28 |
| USDJPY | 3.50 | 0.82 | 0.52–0.59 | 0.48–0.50 |
| EURGBP | 4.82 | 1.21 | 0.81–0.89 | 0.76–0.79 |
| EURCHF | 8.07 | 1.67 | 1.01–1.12 | 0.94–0.98 |
| AUDNZD | 9.40 | 2.59 | 2.00–2.07 | 1.93–1.98 |

In bp, EURUSD (~0.3) and USDJPY (~0.4) are the cheapest. The "quiet" crosses are
the dearest: EURGBP ~1, AUDNZD ~1.9.

## Overnight band fade: no edge once real spreads are paid (`dev.py` → `dev_night.csv`)

12 variants × 8 pairs, entries 20:00–01:00, with the spread filter:
- Pooled, every variant loses −0.9 to −1.1 bp per trade, which is about the spread
  paid. Before costs it makes about zero.
- The best single pair, EURUSD, makes +0.3 bp (t 0.7).

The +0.6 bp "gross edge" the futures version showed was most likely bid-ask bounce
in traded prices. With quotes, it's gone.

## Weekend-gap fade: positive but not significant (`dev.py` → `dev_gap.csv`)

24 variants × 8 pairs. With gaps above 0.2%, most variants are positive, pooled:
- the best is +5.8 bp per trade (t 1.46, 177 trades), with stop 0.5%, target 1:1,
  entry 60 minutes after the Sunday reopen
- its neighbours make +1.5 to +4.9 bp
- it pays a real Sunday spread of about 3 bp

The single-pair leaders (NZDUSD, AUDUSD, t 2–3) come from about 30 trades each and
were picked from 192 pair-variants. They are not evidence.

Published research reports the same effect: weekend gaps in FX tend to reverse.
Development is too short (about 30 trades a year) to confirm it. The sealed
2010–2020 period would add about 350 trades.

## Strategy generator (`generator.py`, `gen_run.py`, `cheap_pairs.py`)

86,400 strategies: 20 hourly signals × mean-reversion/momentum × 12 filters × 3
modes × 60 exits. Every strategy runs on all 8 pairs at real bid/ask. The
in-sample half is 2015–2020 and the out-of-sample half 2021–2026. The null is the
same bars shuffled within each month, with the real spreads.

**With costs, nothing works.**
- 7 strategies passed the in-sample filter, all one idea (fade 6 down hours in the
  afternoon). Out of sample their median Sharpe is −0.20.
- No idea (signal × direction × filter × mode) has a median over its 60 exits that
  is positive in both halves.

**Before costs, there is real predictability.** Real data vs shuffled data:

| | real | shuffled |
|---|---|---|
| top 1% in-sample: median out-of-sample Sharpe | +0.46 | −0.10 |
| top 1% in-sample: share positive out of sample | 81% | 40% |
| ideas positive in both halves | 72 (5%) | 13 (0.9%) |

It is almost all short-term mean reversion: fading runs of down hours, and buying
dips on Mondays.

**It is smaller than the spread on every pair.** For the 72 persistent ideas, the
median edge per trade ranges from 0.03 bp (USDJPY) to 0.56 bp (EURCHF). Costs range
from 0.28 bp (EURUSD) to 1.9 bp (AUDNZD), so every pair nets negative. EURUSD is
closest: 0.24 bp of edge against 0.28 bp of spread.

Restricting to the cheapest pairs, chosen by spread alone, doesn't help. On
EURUSD + USDJPY the best idea turns negative after 2020. Hourly FX mean reversion
is real but smaller than the spread. It pays whoever earns the spread, not whoever
crosses it.

## What the edge is (`edge_anatomy.py`, `weekday_runs.py`, exploratory)

Of the 72 ideas that persisted before costs, 68 are mean reversion. They cluster on
Mondays (22), in the New York afternoon (20) and in the Asian session (12).

**Not the edge:**
- **Fading single big hours.** There is no reversion after an hour more than 2.5 sd
  (−0.3 to +0.04 bp at every delay).
- **Quote noise.** The run-fade survives a 60-minute entry delay.
- **Thin markets.** Spreads at signals are normal (0.96× median).

**Edge 1: slow reversal of multi-hour drifts.** After 6 hourly closes in one
direction, the fade, mean over pairs, makes +0.35 / +0.79 / +1.16 / +0.65 bp over
1 / 4 / 8 / 24 hours. It peaks at about 8 hours. Random hours make about 0.
- It is strongest in AUDUSD and NZDUSD: +3 to +4.5 bp at 8–24 hours.
- USDJPY goes the other way and keeps trending: −1.9 bp at 8 hours, −2.8 at 24.
- EURUSD makes +1.17 bp at 8 hours against a 0.34 bp spread.
The generator's exits (ATR targets, 4/12/24-hour holds) were mostly too short for it.

**Edge 2: the "Monday dip-buying" ideas are a weekday risk cycle.** It is
risk-on on Mondays and risk-off on Thursdays and Fridays. A basket long AUD, NZD,
GBP and EUR vs USD, short JPY and short CHF makes, per FX day:
- Monday +2.1 bp (t 2.4)
- Thursday −1.6 bp (t −1.5)
- Friday −2.0 bp (t −2.0)
Long Monday and short Thursday+Friday nets +0.9 bp per trading day after one spread
per pair (t 1.6, 9 of 12 years positive). It is weak: one of five weekdays,
noticed after the fact.

## Time-series or cross-sectional? (`xsection.py`, `run_decompose.py`, exploratory)

**A plain linear reversal barely exists, in either form.** Fading the last 4–24
hours every period, as the dollar factor or as a dollar-neutral long-laggards /
short-leaders basket, never reaches t 2 in the reversion direction. Over 4 hours
then 24 hours, the cross-section shows momentum (−1.2 bp, t −2.3). The edge is
conditional on a persistent run (6 hours in a row), which a linear signal dilutes.

**After a run, it is mostly cross-sectional: one currency overshoots against the
others.** Fade after 6 hours in a row, 8-hour hold, bp:

| run in … | fade | t |
|---|---|---|
| the dollar factor | +0.78 | 1.2 (and −1.85 at 24 hours) |
| GBP vs the rest | +1.94 | 3.6 |
| EUR vs the rest | +1.34 | 2.5 |
| AUD vs the rest | +1.11 | 1.9 |
| NZD / JPY vs the rest | −0.39 / −0.28 | ~0 |
| CHF vs the rest | −1.04 | −2.0 (it trends) |

A pair's run splits into a dollar part and a currency part, 8 hours, bp (t):

| pair | total | dollar part | currency vs other foreign |
|---|---|---|---|
| AUDUSD | +4.10 | +1.73 (2.4) | +2.44 (4.7) |
| NZDUSD | +3.62 | +1.91 (2.9) | +1.87 (3.2) |
| EURUSD | +1.39 | +0.87 (1.3) | +0.55 (1.3) |
| USDJPY | −1.28 | −1.51 (−2.0) | +0.23 |

The safe havens (JPY, CHF) don't revert; their runs continue.

(Bug fixed on the way: averaging log price levels across currencies with
`skipna=True` changed which currencies the mean covered whenever one was missing,
460 hours of 73,512, and it shifted by thousands of bp. Means are now `skipna=False`.
The January 2015 SNB de-peg day is excluded.)
