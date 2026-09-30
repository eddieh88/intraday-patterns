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
