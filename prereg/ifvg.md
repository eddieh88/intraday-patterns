# Pre-registration: liquidity sweep → inverse FVG (E14)

Written before any code runs, incorporating a practitioner review of a first
draft. Nothing below is revised after seeing results.

## The model, as a chained sequence

The setup is **rejection at a liquidity level, then acceptance through a
counter-gap.** Sweep and IFVG are not two independent filters — the IFVG must
belong to the leg that produced the sweep. Specified for the short side; the
long side mirrors it.

1. **Sweep** of a named level.
2. **Inversion**: within `N` bars, displacement down closes below a *bullish*
   FVG **that formed in the leg up into the sweep**.
3. **Entry**: within `M` bars of inversion, price retraces into the inverted zone.
4. **Invalidation**: price closes back above the zone before entry.

## Definitions, fixed now

**Instrument and resolution.** ES and NQ, **1-minute** bars. This is where the
method is taught; 5-minute single stocks would be a coarsened version on a
different instrument class. Futures verified back-adjusted (large overnight
gaps no more concentrated in roll windows than chance: 25 observed, 21
expected).

**Named levels** (for the sweep): prior day high/low, prior session high/low
(Asia 19:00-04:00, London 03:00-11:30, NY 09:30-16:00 ET), and confirmed swing
highs/lows.

**Swing points.** A k-bar fractal: bar *i* is a swing high if its high exceeds
the `k` bars each side. **Only usable from bar `i+k` onward** — a pivot is not
known until the bars confirming it have closed. `k = 3`. This is the single
easiest place to reintroduce look-ahead and is enforced explicitly.

**Sweep.** Price trades beyond the level by at least `PEN` and the candle
closes back inside the prior range.
- primary: close-back-inside on the **same candle**
- secondary: within 2-3 bars
- `PEN = 0.10 x ATR(14)`, so a one-tick poke through PDH does not qualify.
  Without this the sample is dominated by trivial penetrations.

**FVG.** Three consecutive bars, `high[i] < low[i+2]` (bullish) or
`low[i] > high[i+2]` (bearish). Filters, all required:
- gap width `>= 0.25 x ATR(14)`
- middle candle range `>= 1.5 x ATR(14)`, closing in the top/bottom third of
  its own range (displacement)
- **belongs to the leg into the sweep**: the FVG's third bar falls between the
  most recent swing low before the sweep and the sweep bar itself
- **stacked gaps**: overlapping FVGs are merged into one zone, using the
  outermost edges
- **max age**: `N = 20` bars from FVG formation to inversion

**Inversion.** A **body close** beyond the entire zone.
- primary: close below `high[i]` for a bullish FVG (the whole zone)
- secondary: close beyond the zone **midpoint** (consequent encroachment)
- a close *into* the zone is ordinary mitigation, not inversion

**Entry.** Retracement into the inverted zone, `M = 20` bars max.
- entry at the **near edge** of the zone
- requires a **trade-through**, not a touch: the bar's range must cross the
  level, since on OHLC bars a touch is not a fill and assuming otherwise is
  systematically favourable

**Stop.** The **sweep extreme** plus `0.25 x ATR(14)`. That is the level the
setup claims is defended, and it is unambiguous — unlike "the nearest high
before the IFVG formed".

**Target.** Opposite-side liquidity: the nearest confirmed swing low below
entry (for a short), using only pivots confirmed before entry.
- **skip the trade if the target is under 1.5R** — practitioners filter this way
- **time exit**: end of the RTH session
- the **same** stop and target construction is applied to the random baseline,
  so the comparison isolates entry rather than target geometry

**Frequency.** **First signal per instrument per day.** Decided now.

## HTF conditioning — pre-registered as variables, not filters

Recorded for every trade and reported as splits, not used to select:
- **premium/discount**: entry above or below the 50% of the prior day's range
- **HTF gap direction**: direction of the most recent unfilled 1-hour FVG
- **daily bias**: prior day closed in the upper or lower third of its range

**If the core setup is null but the premium/discount split is not, that is the
most informative outcome available here.**

## The statistic

Mean R and its t-stat **clustered by session date** — every t-stat in the
intraday series so far was inflated by treating trades on the same day as
independent. Reported against a random-entry baseline using identical stop,
target and filter construction.

## Decision thresholds

**WORKS** — mean R > +0.10, clustered t > 3, and materially above the random
baseline on the same days.
**DEAD** — mean R <= 0 against the baseline.
**AMBIGUOUS** — anything else.

## Prior, and the bounded conclusion

**Weakly negative on the mechanical core.** E4 already tested sweep-and-reverse
on the opening range and refuted it (breaks continued; fading lost 5.7bp,
t=-9.3) — though it lacked the inversion step, which is the part that is
genuinely new here.

**What this cannot conclude.** The full discretionary narrative — order blocks,
BPRs, "does the story make sense" — is not mechanised. A null result bounds how
much of the method lives in the pattern versus in the discretion. It does not
refute the method.
