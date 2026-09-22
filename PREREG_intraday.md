# Pre-registration: timing decay, and did the overshoot move intraday?

Written before any minute bar is examined. Nothing below is revised after seeing
results.

## Why

Every net result in this project sits inside the 1bp–2bp band where conclusions
flip, and one basis point is worth more than the alpha we measured:

| strategy | turnover | 1bp costs | book vol | = Sharpe |
|---|---|---|---|---|
| reversal L=30 | 0.25 | 0.63%/yr | 2.71% | **0.23** |
| reversal L=1 | 1.45 | 3.65%/yr | 3.47% | **1.05** |

Against a best-case measured alpha of +0.35 and an honest one of −0.02. We have
been optimising the smaller term.

Separately, Step 4 established that the daily overshoot still forms but arrives a
day later and about a fifth the size. The obvious untested possibility is that
the *original* same-day overshoot still forms and now corrects **within the
session**, invisible to close-to-close data.

## Test A — timing decay

**Claim.** A strategy whose signal must be computed from prices it also trades at
is not executable. Recomputing the signal at 15:45 and filling at the official
close measures the gap.

Residuals rebuilt from 15:45 prices (last trade at or before 15:45), factor
model and universe otherwise identical to `src/mp_residuals.py`. Strategy
returns still measured close-to-close, so only the *signal* moves.

**Statistic:** ratio of 15:45-signal Sharpe to close-signal Sharpe, 2017–2026,
gross, for L=1, L=5, L=30.

**Prediction, recorded now:** large decay for L=1, negligible for L=30 — because
a one-day signal is mostly the last fifteen minutes, and a thirty-day cumulative
is barely moved by them. If L=30 degrades materially, the slow strategy was never
as executable as this project has assumed and every net figure for it is
optimistic.

## Test B — did the overshoot move intraday?

**Claim.** If same-day overshoots still form, a residual computed over part of the
day should predict reversal over the remainder.

Construction: for each name-day, split the session at 12:00. Compute a morning
residual (09:30→12:00 return minus its beta-weighted factor return, betas and
factors from the daily model, strictly prior) and an afternoon return
(12:00→16:00). Cross-sectional correlation of morning residual with afternoon
return, per day, averaged by era.

**Statistic:** mean cross-sectional correlation, by era. The 2002–2008 value is
the benchmark — if intraday reversal was always present, its persistence tells us
nothing new.

**Thresholds:**
- **MOVED INTRADAY** — 2017–2026 correlation more negative than −0.010 **and**
  more negative than 2002–2008. The overshoot relocated rather than shrank.
- **NOT INTRADAY** — |correlation| ≤ 0.005 in 2017–2026, or it is weaker than
  2002–2008. The overshoot genuinely shrank, and daily data was not hiding it.
- **AMBIGUOUS** — anything else, reported as such.

## Universe and sample

Top 900 by trailing 21-day dollar volume, point-in-time, from the
survivorship-free panel. Minute bars are ~20MB/day and 95GB in full, so a
stratified sample: **20 trading days per year, evenly spaced, 2002–2026** (~500
days). Sample fixed by calendar rule before download, not chosen after seeing
results.

## Known hazards, recorded in advance

- **Bid-ask bounce.** Minute-bar closes alternate between bid and ask, which
  manufactures negative autocorrelation at short horizons. A morning-to-afternoon
  split at 12:00 is far enough apart that bounce should not dominate, but any
  intraday reversal found at shorter horizons would be suspect for this reason.
  Do not test sub-hourly splits.
- **Opening auction.** The 09:30 print is an auction, not a trade, and behaves
  differently. Morning returns are measured from the first bar **after** 09:35.
- **Thin names.** Median bars per symbol per day is ~114, far below the 390
  minutes of a session, so most symbols do not trade every minute. Restricting to
  the top 900 by dollar volume should avoid this; verify bars-per-day per name
  and exclude any name-day with fewer than 200 bars.
- **This is the fifth test on overlapping data.** Reversal, liquidity bands,
  characteristics, delayed overshoot, now this. Not independent evidence.
- **Test A cannot measure impact or fill quality.** It bounds signal decay only.
  A favourable result does not establish that 1bp is achievable — that still
  requires real orders.
