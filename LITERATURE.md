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

---

# The ML asset-pricing literature, and where this project sits in it

Seven papers, each connecting to something this project hit directly — in three
cases to a mistake we made and could not name at the time.

## Avramov, Cheng & Metzker (2023) — the paper we independently re-ran

*Machine Learning vs. Economic Restrictions*, Management Science.

ML return forecasts lose most of their profitability once microcaps, distressed
and unrated firms are excluded and costs are charged. What survives is
concentrated where **limits to arbitrage are high**.

This is the closest paper to what this project did, and we arrived at it
backwards — measuring gross first, then adding turnover, borrow, delisting and
volume caps until nothing was left. Their headline is our Part 2 and Steps 1–7.

**Where we disagree, and it is informative.** They find ML signals strongest
where arbitrage is costliest. Our liquidity-band test found **no gradient at
all** — gross Sharpe within one standard error of zero from $160M median daily
volume down to $1M. Two possible reasons, and we cannot separate them: they test
*characteristic-based* signals while we tested *price-based* reversal, and their
sample predates ours. If the answer is the former, it says the residual-reversal
family is uniquely dead while characteristic signals merely retreat downmarket.

## Gu, Kelly & Xiu (2021) — we asked their question and answered it badly

*Autoencoder Asset Pricing Models*, Journal of Econometrics.

Factor loadings are a **nonlinear function of firm characteristics**, estimated
by a neural network, inside a constrained autoencoder. It strictly generalises
IPCA (the linear-beta special case) and keeps the no-arbitrage factor structure
rather than forecasting returns directly. It beats IPCA, PCA and observable
factors on ~94 characteristics.

Midway through this project we asked whether the beta step could be nonlinear and
tested quadratic and asymmetric betas. Both made things **worse** — residual
AR(1) went to +0.0149 and +0.0749 against the linear −0.0037, which is
overfitting: 10–20 parameters on 60 daily observations.

GKX shows the error precisely. **We put the nonlinearity in the wrong argument.**
Nonlinear *in the factors*, fit on 60 days, is hopeless. Nonlinear *in
characteristics*, fit across the whole panel, is the version that works — the
parameters are shared across every stock, so the effective sample is enormous.

This is directly actionable: we hold a survivorship-free panel, 209 OSAP
characteristics, and a crosswalk validated at r = 0.9998 on a held-out signal.
Every result in this project used PCA-5. The authors' own best arm was IPCA at
4.16 and we never built it, let alone its autoencoder generalisation.

## Kelly, Malamud & Zhou (2024) — and why our null result is not a counterexample

*The Virtue of Complexity in Return Prediction*, Journal of Finance.

Models with more parameters than observations can beat parsimonious ones out of
sample; out-of-sample R² can stay negative while the timing strategy's Sharpe
rises.

We found architecture did not matter — 769 parameters and 1,785 parameters gave
4.92 and 4.77, inside noise. **That is not evidence against VoC**, because we
were never near the regime it describes: 770 parameters against 3.9M (day, stock)
observations is deeply *under*-parameterised. c = P/T ≈ 0.0002, not ≥ 1.

Nagel's critique — that ridgeless regression on random features with short
windows behaves as a kernel smoother reproducing vol-timed momentum rather than
learning from predictors — has a miniature analogue here. Our fitted 30-lag ridge
filter **collapsed onto lag 1** (+0.77, −1.00 on the last two coefficients),
rediscovering one-day reversal from 30 free parameters and then underperforming
it (2.70 vs 3.14). Flexible estimator, simple recovered signal, worse than the
simple signal directly. Same shape of finding at a far smaller scale.

## Chen, Pelger & Zhu (2024) — the objective, not the architecture

*Deep Learning in Asset Pricing*, Management Science.

The SDF is `M = 1 − w'R` with weights a network function of characteristics and
an LSTM-compressed macro state, trained to satisfy **conditional no-arbitrage
moments** via an adversarial network choosing the hardest instruments to price.

Same senior author as the paper we replicated. Note what changes between them:
DLSA optimises portfolio Sharpe; CPZ optimises a no-arbitrage condition. Both
papers' contribution is the **objective**, not the network.

That is the single clearest lesson of this project, arrived at empirically: three
architectures within noise of each other, while the objective — Sharpe with no
cost term — produced a book with 1.64% volatility that needed 6× leverage and
died on turnover. The adversarial instrument search is also, structurally, an
automated null-hunt: a second model seeking the assets the first cannot price.

## Jiang, Kelly & Xiu (2023) — their caveat is our central result

*(Re-)Imag(in)ing Price Trends*, Journal of Finance.

Render OHLC, volume and moving averages as images; train CNNs to predict return
sign. Very high Sharpe at weekly horizons, patterns transfer across horizons and
countries, and the signal is not simply momentum or reversal.

Their stated caveat — *the gross numbers are strongest where turnover and
trading costs bite hardest* — is the conclusion of this entire project, stated as
a footnote.

One genuine difference worth noting: their input carries **volume and intraday
range**, ours carried only the cumulative residual path. When we conditioned on
relative volume we found the sign flip (−0.0182 → +0.0024), so volume does carry
information our representation discarded.

## Leippold, Wang & Zhou (2022) — the "where", not the "what"

*Machine Learning in the Chinese Stock Market*, JFE.

The same methods yield substantially stronger predictability in China, where the
investor base is retail-dominated and short-selling is constrained. Liquidity
characteristics dominate variable importance, unlike the US. Predictability
concentrates in small and retail-heavy stocks, and shrinks once T+1 settlement,
price limits and costs are imposed.

This is the sharpest answer to "where should we look" that the literature gives.
Our conclusion was that documented edges in US large caps are gone; theirs is
that the same methods work where the marginal investor is less sophisticated.
**Different market, not different model.**

## Bianchi, Büchner & Tamoni (2021) — different asset class

*Bond Risk Premiums with Machine Learning*, RFS.

Nonlinearity in macro variables predicts Treasury excess returns; the premia are
countercyclical and the gains are not replicated by linear shrinkage on the same
inputs.

Relevant as proof the approach is not equity-specific. Our infrastructure is
equity-shaped, but the method — pre-register, null, cost, walk-forward — is not.

---

# A way forward the literature actually supports

The papers that work share three properties. We had one.

| | GKX / CPZ | this project |
|---|---|---|
| inputs | firm characteristics | **prices only** |
| structure | factor model / no-arbitrage | free-form |
| innovation | the objective | Sharpe objective ✓ |

**The concrete next step is the autoencoder factor model on our own data**, and
it is well-defined rather than exploratory:

1. Betas as a **neural function of characteristics**, factors as
   characteristic-managed portfolios — GKX's constrained autoencoder.
2. Fit on the **survivorship-free panel** with the **209 OSAP characteristics**
   already joined through a validated crosswalk.
3. Benchmark against PCA-5, IPCA (linear-beta special case), and the autoencoder,
   on the **same residuals, same harness, same costs** as everything else here.
4. Judge on **net-of-cost** performance and against a null, because the whole
   contribution of this project's method is that gross numbers mislead.

This does three things at once: it is the principled version of the nonlinear-beta
test we botched, it builds the authors' own best arm which we never did, and it
puts characteristics into a project that has only ever seen prices.

Honest expectation: Avramov, Cheng & Metzker says most of it will not survive
costs. But it is the first time in this project that the *inputs* would change
rather than the model — and our own evidence says inputs were always the
constraint.
