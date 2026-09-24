# Pre-registration: Opening Range Breakout on "Stocks in Play"

Written before any code runs. Nothing below is revised after seeing results.

## Why this one is different

Every intraday test so far (E1-E6) used the top 100-200 names by **absolute**
dollar volume — the same mega-caps every day. Zarattini, Barbon & Aziz (2024)
claim the edge exists only in stocks that are unusually active *that morning*.
That universe is orthogonal to everything we have tested, which is the single
best reason to run this.

Their reported result: Sharpe 2.81, ~1,600% cumulative, 2016-2023, near-zero
beta. A published number to beat or fail against, rather than an open question.

## Rules, fixed now

**Universe.** Top 1,000 by trailing dollar volume, price > $5, ATR(14) > $0.50.
**Stocks in Play.** Each day rank by
`relvol = first-5-min volume / mean(first-5-min volume, prior 14 sessions)`
and take the **top 20**. Computed from the 09:30-09:35 bar only, so it is known
at 09:35 and uses no later information.

**Opening range.** The 09:30-09:35 bar. Long only if that bar closed up, short
only if it closed down — direction comes from the range itself.

**Entry.** First 5-min close beyond the OR high (long) / low (short), after
09:35 and before 16:00.

**Stop.** Two variants, both declared now, both reported:
  - `A` opposite side of the opening range
  - `B` 1.5 x ATR(14) from entry, as the paper describes

**Exit.** Market close. **No profit target** — E6 showed 13.2% of trades timed
out averaging +1.84R, so a 3R target was cutting winners.

**Costs.** 2bp round trip, and stops fill at `min(stop, next open)` so gaps
through are charged.

## The statistic

Mean R per trade and its t-stat, plus the outcome mix (target / stop / close).
Reported for both stop variants and for the full universe vs top-20-relvol, so
the relative-volume filter is isolated as its own effect.

## Decision thresholds

**WORKS** — mean R > +0.05 with t > 3, in BOTH stop variants, and materially
better in the top-20 relvol subset than in the full universe.
**DEAD** — mean R <= 0 in either variant.
**AMBIGUOUS** — anything else.

## Prior, recorded now

**Weakly negative, but the least negative prior of anything tested today.**
Six intraday claims have failed. But this one has a mechanism (news-driven
participation is not the same population as habitual mega-cap flow), a
published result, and a filter we have never applied. The critique of the paper
— no independent post-selection validation, simplified execution, no slippage
in some models, retrospective parameter search — describes exactly the failure
modes that bit us today, so the reported 2.81 Sharpe is not the expectation.

## Known hazards

- **Relative volume is a survivorship-flavoured filter.** A stock is "in play"
  because something happened; the question is whether that is knowable at 09:35
  without hindsight. It is, by construction here, but the universe screen must
  use only prior-day dollar volume — the 19%/yr lesson from Step 9.
- **Costs.** Stocks in play are volatile and may be wider spread than the
  mega-caps where our 1-2bp estimates came from.
- **Seventh intraday test.** Multiple testing applies.
