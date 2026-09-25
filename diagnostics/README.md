# diagnostics

One-off scripts that produced results quoted in the write-ups. Kept so the
numbers can be reproduced, not because they are reusable.

| script | what it established |
|---|---|
| `friction_decomposition.py` | **the most important one.** Splits a trade result into gross / costs / slippage across three stop widths. Showed the universal -0.1R in E6-E13 was my stop width, not thirteen signal failures: gross is +0.013 to +0.018R regardless, slippage is 0.002R, and the same 2bp is -0.135R at a half-bar stop but -0.034R at a two-bar stop. |
| `breakretest_param_sweep.py` | 18 variants of the daily break-and-retest parameters. bounce-vs-no-breakout survived 17/18 at t>2; bounce-vs-immediate survived 2/18. |
| `breakretest_paired.py` | same events, two entry timings, to separate entry timing from which breakouts produce retests. |
| `rr_ratio_sweep.py` | expectancy across R:R from 0.5 to 10. Excess win rate rises monotonically with the ratio — fat tails — so 1:3 is not optimal. |
| `gapfill_stops.py`, `atr_stops.py` | stop placement variants; found the tiny-denominator artifact that produced a fake +11R on one arm. |
| `traditional_factors.py` | classic factors (value, momentum, profitability...) on the corrected monthly panel, as the benchmark the autoencoder had to beat. |
| `delisting_audit.py` | quantified dropped delisting returns: 0.46% of name-months at a median last price of $37, mostly M&A rather than bankruptcy. |
| `market_beta.py` | long/short decomposition and borrow-rate sweep. Contains a bug — it took the Sharpe of OLS residuals, which are zero-mean by construction, so its "hedged Sharpe +0.00" was meaningless. Corrected in FINDINGS_autoencoder.md. |
