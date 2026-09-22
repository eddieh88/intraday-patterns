# What of this is already known

Searched after the measurements, not before. Most of what this project found
independently is in the literature — which is itself consistent with the
project's own conclusion, and worth stating plainly rather than burying.

## Step 7 — index reversion — is a published result

**Baltussen, van Bekkum & Da (2019), "Indexing and stock market serial dependence
around the world", *Journal of Financial Economics* 132(1), 26–48.**
[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2786516) ·
[PDF](https://www3.nd.edu/~zda/Indexing.pdf)

Across 20 indexes in 15 countries, index return serial dependence was **positive
until the 1990s and switches to negative from the 2000s**. They tie it to the
growth of index products — futures, ETFs, index mutual funds — show it is not a
time trend, confirm it in the cross-section of indexes, and attribute it in part
to **the arbitrage mechanism between index products and the underlying stocks**.

That is our Step 7, including the mechanism. We measured equal-weight market
AR(1) going −0.0293 → −0.0750 and cap-weight at −0.0838, and proposed indexing
as the cause. They established it, with far better identification (Nikkei 225
weight changes, S&P 500 membership events) than a time-series comparison can
provide.

## The economic interpretation is Nagel's

**Nagel (2012), "Evaporating Liquidity", *Review of Financial Studies* 25(7),
2005–2039.** [NBER](https://www.nber.org/papers/w17653)

Short-term reversal returns are the returns to **liquidity provision**, strongly
time-varying and predictable by VIX, rising sharply in turmoil. This is the frame
we arrived at for why reversal paid at all, and why 2008–2009 shows up as a
local peak in our per-block series.

## Step 3 — the characteristics result — is also documented

**Chordia, Subrahmanyam & Tong (2014), "Have capital market anomalies attenuated
in the recent era of high liquidity and trading activity?", *Journal of
Accounting and Economics* 58, 41–58.**
[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2029057)

Most anomalies have attenuated; returns roughly **halved after decimalization**,
with the decline tied to hedge fund AUM, short interest and turnover.

Together with **McLean & Pontiff (2016)** on ~58% post-publication decay, this is
our Step 3: a 209-characteristic composite netting +0.24, inside its own null,
with +0.20 of that coming from sign alignment chosen in-sample.

## One paper that sits in tension with our stock-level result

**Ben-David, Franzoni & Moussawi (2018), "Do ETFs Increase Volatility?",
*Journal of Finance* 73(6).**
[Wiley](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12727)

Higher ETF ownership raises **non-fundamental** volatility in the underlying and
produces departures from a random walk **at intraday and daily frequency, with
reversals** — noise propagating from ETFs into constituents via arbitrage.

That is the opposite sign to our stock-level finding: they document ETF ownership
*creating* single-stock reversal; we measure single-stock residual reversal going
to zero (−0.0269 → −0.0018) and flipping to continuation for large moves.

Two readings, and we cannot distinguish them with what we have:

1. **Reconcilable by period.** Their sample ends around 2015. ETF arbitrage may
   push noise into constituents in an earlier regime and absorb it efficiently
   enough by 2017–2026 that only the index-level component survives.
2. **Genuinely in tension**, in which case our residual construction or universe
   differs in some way that matters.

Testing this properly would mean sorting stocks by ETF ownership and measuring
residual AR(1) within each bucket — the natural next experiment, and one their
identification strategy is built for.

## What does not appear to be documented

- **That the DLSA paper's own claim of "non-declining profitability" fails on its
  own residuals** (t = −8.92, 7.38 → 2.46 across its own out-of-sample window).
  That is specific to arXiv:2106.04028 and, as far as we can find, unreported —
  including by the independent replication that reached parity on the headline
  numbers.
- **The two sides measured together.** Baltussen et al. document the index side;
  the attenuation literature documents the anomaly side. Measuring residual AR(1)
  collapsing to zero *while* index AR(1) doubles, on one dataset with one
  construction, is the complement to their result rather than a new one.

## What this means for the project

Seven exploration steps, and the literature says: the two that produced real
measurements were rediscoveries, and the five negatives were predictable from
published work on anomaly attenuation.

That is not a failure of method — it is the method working. The measurements
agree with careful published work we had not read, which is the outcome you want
from a pipeline validated against known answers. But it does sharpen the standing
conclusion: **searching where the literature has already looked produces results
the literature already has.**
