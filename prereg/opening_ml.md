# Pre-registration: what drives returns in the hour after the opening range?

Written before any code for this study exists and before any feature or target is
computed. Changes are dated amendments made before the data they concern is read.

## Question

Across each day's top 100 US stocks, does anything known at 10:00 rank their
returns from 10:00 to 11:00? If so:
- which drivers matter, and are they stable over time?
- can two or three of them make a simple long-short rule that pays after costs?

The 09:45 selection study (`selection.md`) found nothing for a narrower question:
does each stock's own opening move persist? This study asks something different.
It ranks stocks against each other, so the market's direction cancels, and it adds
effects from the literature that the selection study did not include:
- same-time-of-day persistence (Heston, Korajczyk & Sadka 2010)
- overnight-versus-intraday reversal (Lou, Polk & Skouras 2019)
- the relative strength of the opening move
- multi-day momentum and reversal

## What has already been seen

E1–E18 and the structural-stop study read 2021–2026 bars for other questions. The
holdout below was read once (2026-10-01) for `structure_stops.md`, with different
entries and outcomes. No cross-sectional 10:00–11:00 target has been computed on
any period.

## Data

- **Universe:** each day's top 100 from `cache/intraday_pool.parquet`
  (point-in-time).
- **Development:** 2021-01-19 → 2025-03-31. **Holdout:** 2025-04-01 → 2026-09-21,
  sealed by `lib/holdout.py`, read once under *Holdout*.
- **Bars:** 5-minute, from `cache/mp5min`, stamped at bar start. Regular session
  09:30 to the close, half-day aware (`selection/session_summary.session_close`).
- Daily quantities (closes, full-session highs and lows, ATR) are built from the
  bars here, not from `cache/intraday_daily.parquet`. That table's prior-day
  high and low cover 11:00–16:00 only.

## Target

- **Return:** r = close of the 10:55 bar / open of the 10:00 bar − 1.
- **y:** r minus the equal-weighted mean of r across that day's universe (the
  stock's return relative to the day's top 100).
- **Model target:** the cross-sectional rank of y each day, scaled to [−0.5, 0.5].
  It is robust to outliers and to volatility changing over time.
- A name-day without a 10:00 and a 10:55 bar is dropped.

## Features — all known by the close of the 09:55 bar

Stock-level features are converted to cross-sectional ranks each day, scaled to
[−0.5, 0.5]. The two market-level features are kept raw, as context.

| group | feature |
|---|---|
| opening (09:30–10:00) | return 09:30 open → 09:55 close; the 09:30–09:45 and 09:45–10:00 halves separately; range / ATR20; volume / its own 09:30–10:00 mean over the prior 20 sessions; where the 09:55 close sits in the range (0–1); 09:55 close / the window's VWAP − 1 |
| relative opening | opening return minus the universe median opening return that day |
| overnight | gap: 09:30 open / prior close − 1; pre-market return: last pre-market close / prior close − 1; pre-market dollar volume / its 20-session mean |
| same time of day | the stock's 10:00–11:00 return yesterday; its mean 10:00–11:00 return over the prior 5 and 20 sessions |
| prior days | yesterday's close-to-close return; yesterday's open-to-close return; yesterday's last-hour (15:00 to the close) return; 5- and 20-session close-to-close returns |
| levels | (09:55 close − yesterday's full-session high) / ATR20, and the same for the low; the 09:30 open's position in yesterday's range (0–1) |
| volatility | ATR5 / ATR20 (full-session daily ranges); ATR20 / price |
| size and liquidity | log price; rank in the day's pool; 20-session dollar volume |
| market context (raw) | the universe median opening return; the universe median ATR20 / price |
| calendar (raw) | day of week |

ATR5 and ATR20 are means of full-session daily ranges over the prior 5 and 20
sessions. A feature needing more history than exists is missing; LightGBM handles
missing values natively, and linear baselines impute the day's median rank (0).

**Leak audit (a test that can fail):** the feature builder runs on a hand-built
day, then again with every bar stamped 10:00 or later replaced. All features must
be identical.

## Walk-forward (development only)

- **Test blocks:** 2022 H1, 2022 H2, 2023 H1, 2023 H2, 2024 H1, 2024 H2, and 2025
  Q1 (seven).
- **Training:** for each block, every development session before it, minus a
  5-session gap.
- **Validation:** the last 15% of training sessions are held out for early stopping.
- **Model (fixed in advance):** LightGBM regression with num_leaves 15,
  learning_rate 0.03, min_data_in_leaf 500, feature_fraction 0.8, bagging_fraction
  0.8 (every 1 tree), lambda_l2 1.0, at most 1,000 rounds, early stopping after 50
  rounds without improvement, seed 7.
- **Baselines, same folds:**
  - **B1, opening momentum:** rank by the relative opening return (the E18 effect,
    cross-sectionally)
  - **B2, ridge:** on the same features, α chosen from {1, 10, 100, 1,000, 10,000}
    on the same validation sessions

## Metrics (out of sample, pooled over the seven blocks, by block)

- **IC:** the daily Spearman correlation between the prediction and y; its mean,
  and t over days.
- **Spread:** each day, long the top fifth and short the bottom fifth by
  prediction, equal-weighted, entered at the 10:00 open and exited at the 10:55
  close. Mean daily spread (long minus short), gross, and net of 3 bp round trip per
  stock (6 bp per day for the dollar-neutral spread) and of 6 bp (12 bp per day).
  t over days.
- **Drivers:** the mean |SHAP| of each feature (LightGBM `pred_contrib`) per fold;
  each feature's rank across folds; and each feature's own IC per block.

## Decisions (development)

- **The model has signal** if all hold:
  - pooled mean IC > 0 with t ≥ 3.0
  - IC positive in at least 5 of 7 blocks
  - IC above B1's: the paired daily difference has t ≥ 2.0
- **The model's strategy pays** if the 6 bp net spread is > 0 with t ≥ 2.75, and is
  positive in at least 5 of 7 blocks.
- **Distillation**, whether or not the model passes:
  - the "stable drivers" are the features ranked in the top 5 by mean |SHAP| in
    at least 5 of 7 folds, up to 3 of them
  - the rule is the equal-weighted mean of their cross-sectional ranks, each
    signed by the sign of its own IC on that fold's training data
  - it is evaluated walk-forward like the model
  - it passes on the same spread criteria as the model's strategy

## Holdout

Run once, only for whatever passed in development: the model's strategy, the
distilled rule, or both. Confirmed if the 6 bp net spread is > 0 with t ≥ 2.0 over
the holdout days. The model for the holdout is trained on all development sessions
with the same settings; the distilled rule's signs come from all of development.
If nothing passes, the holdout stays sealed.

## Prior

**Weakly positive on the IC, negative on paying after costs.** Cross-sectional
intraday effects are documented, so a small positive IC (about 0.01–0.03) is
plausible. But the spread has to clear 6 bp a day, and this repo's intraday edges
have so far been 1–2 bp. Expect the drivers to be the opening-relative return,
same-time-of-day persistence and the gap.

## Amendment 1 — 2026-10-06, before any feature or target is built: macro and sector

**Data:**
- `cache/mp_futures_1min`: back-adjusted continuous contracts on 1-minute bars,
  New York time, 2021–2026
- `cache/mp_etf_5min`: ETFs on 5-minute bars

"Macro move" means the change from the prior session's last regular bar (the
1-minute bar stamped 15:59, or 12:59 on a half day) to the close of the 1-minute
bar stamped 09:58. That close is at 09:59, before the 10:00 entry. Returns are
log returns. For VX the change is in points.

**Raw macro context (one value per day; not ranked):**

| series | what it stands for |
|---|---|
| ES move; ES 09:30–09:58 move | the market overnight and at the open |
| NQ minus ES move; RTY minus ES move | tech against broad; small against large |
| ZN move | 10-year rates (price up = yields down) |
| US move minus ZF move | the curve: 30-year against 5-year |
| DX move | the dollar |
| J1 move | the yen, as a risk-off gauge |
| CL move; GC move | oil; gold |
| VX change; VX level at 09:58 | the change in expected volatility; its level |
| BTC move | risk appetite |

**Stock-level macro exposure (ranked each day):**
- For each of ES, ZN, DX, CL and VX, β is the stock's beta to that series. It is
  estimated from the prior 60 sessions of close-to-close daily returns (VX in
  point changes), with at least 40 of them.
- The feature is β × today's macro move: the move each stock "should" make from
  that macro shock. That gives five features.

**Sector (ranked each day):**
- Each stock is assigned the one of XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLB,
  XLRE, XLC and SMH whose daily returns correlated most with its own over the prior
  60 sessions. This is the rule from the selection study.
- **Features:**
  - the stock's 09:30–10:00 return minus its sector ETF's (its own move, with the
    sector removed)
  - the sector ETF's 09:30–10:00 return minus SPY's (sector strength at the open)

**The leak audit covers these too:** with every futures bar stamped 09:59 or later,
and every ETF bar stamped 10:00 or later, replaced, all features must be identical.

The feature count rises from 29 to 45. Nothing else changes. Prior: macro surprises
matter for each stock's own direction more than for ranking stocks against each
other. Expect the sector-relative opening return to matter most of the additions.

## Amendment 2 — 2026-10-06, before any feature or target is built: do the drivers change?

The walk-forward reports drivers by fold. Differences between folds are partly
noise (about 120 days a block), so the change itself is tested.

**1. Over time.** For each feature, compute its own daily IC (the Spearman
correlation with y) in each of the 7 blocks, with a standard error over days. Run
Cochran's Q across blocks.
- A feature's effect **changes over time** if Q's p-value < 0.05 / (number of
  features).
- Report I² (the share of variation beyond noise) for every feature.

**2. By regime, defined before the fact.** Each day gets three labels, all known
by 10:00 from prior data only:
- **volatility:** the VX level at 09:58, in thirds, cut at the prior 250 sessions'
  terciles (expanding until there are 250)
- **trend:** ES's 20-session return up or down at the prior close
- **rates:** ZN's 20-session move up or down at the prior close

For each feature and each label, compare its daily IC between regimes (Q across
the groups), with the same Bonferroni threshold.

**3. Does knowing the regime help, out of sample?** Run only for features passing
1 or 2. A regime-switching version of the distilled rule uses, in each regime, the
signs and feature set chosen from that regime's training days only. It must beat
the static distilled rule: the paired daily spread difference, net at 6 bp, with
t ≥ 2.0 over the walk-forward test days.

**4. LightGBM's own interactions.** Report the mean |SHAP interaction| for the top
pairs per fold, with no verdict.

**Power:** a block has about 120 days. With daily IC standard deviations near
0.10, a block's IC has a standard error near 0.009. So only regime differences of
about 0.025 or more in IC are detectable.

## Amendment 3 — 2026-10-06, after a 3-day smoke test of the builder, before the build

The VX futures series is back-adjusted, which keeps its day-to-day changes but
makes its level drift: it read about 70 in June 2023, when the VIX was near 14.
**Changes:**
- The "VX level" feature is replaced by ES's realized volatility over the prior 20
  sessions (the standard deviation of its daily log returns, annualized). The VX
  change feature stays.
- Amendment 2's volatility regime uses that measure in place of the VX level,
  with the same rule (thirds cut at the prior 250 sessions' terciles).

The smoke test read 300 name-days (2023-06-01 to 06-05) only, to check scales and
missing values. No target was compared with any feature.

## Results — development, 2026-10-06

`python3 ml/build.py && python3 ml/walk.py && python3 ml/drivers.py`.
- **Data:** 104,052 name-days over 1,044 sessions, 50 features (34 ranked
  across stocks, 16 context).
- **Out of sample:** the seven blocks from 2022-01 to 2025-03, 813 days.

| | IC | t | blocks + | spread, gross bp/day | net 6 bp | t | blocks + (net) |
|---|---|---|---|---|---|---|---|
| LightGBM | +0.011 | 1.08 | 4/7 | +4.27 | −1.73 | −0.45 | 4/7 |
| ridge | +0.003 | 0.26 | 4/7 | +0.45 | −5.55 | −1.69 | 0/7 |
| B1, opening momentum | −0.002 | −0.27 | 3/7 | +3.10 | −2.90 | −1.06 | 3/7 |

**The model has no signal (fail), and its strategy does not pay (fail).**
- LightGBM stopped after 1–46 trees per block, and ridge chose its largest
  penalty in 6 of 7 blocks: the same "nothing to learn" pattern as the selection
  study.
- The model's IC by block: +0.015, +0.046, +0.053, +0.014, −0.038, −0.012, −0.020.
  It was positive through 2023 and negative from 2024.
- LightGBM minus B1 IC: +0.013 (t 1.03).

**Drivers (mean |SHAP|):**
- **atr_pct, the stock's volatility (ATR20 / price):** top 5 in 7/7 folds. Its own
  IC is negative in 6 of 7 blocks (−0.067 to +0.018). Calmer stocks beat
  more volatile ones from 10:00 to 11:00.
- **Market context:** ES's 09:30–09:58 move (top 5 in 6/7), Russell minus ES
  (6/7) and market volatility (4/7). These only act through interactions; in part
  this is beta: a stock's volatility matters more on mornings the market moves.
- **Same-time-of-day persistence:** tod1 has IC +0.032, +0.007, −0.006, −0.018,
  +0.028, +0.020, +0.027 by block. It is positive in 5 of 7, small, and rarely in
  the model's top 5.

**Distilled rule, long the calmest fifth and short the most volatile:** only atr_pct
met the stability bar. IC +0.026 (t 1.91), positive in 5 of 7 blocks; gross
spread +6.57 bp/day (t 1.36); **net of 6 bp, +0.57 bp/day (t 0.12). Fail.**

**Do the drivers change? (Amendment 2)**
- **Over time:** no feature's IC differs across blocks beyond noise. The
  smallest p is 0.018 (pool rank and dollar volume), against the Bonferroni
  threshold of 0.0015.
- **By regime:** none differs between volatility thirds, ES trend up/down or ZN
  moves up/down. The smallest p are 0.019 (CL exposure, by rates), 0.023 (the
  09:45–10:00 return, by trend) and 0.032 (5-day same-time persistence, by
  volatility), against 0.00049. With 136 such tests, a few p-values near 0.02 are
  what chance produces.
- So part 3 (regime switching) does not run. Given the power (differences of
  about 0.025 in IC are detectable), the drivers' effects are stable, or vary by
  too little to measure. Part 4 (SHAP interactions) was not run, because no
  model or feature passed.

**Nothing passed, so the holdout stays sealed.** The low-volatility tilt is the one
consistent cross-sectional effect here, about 6–7 bp a day before costs. That is
roughly the cost of trading it.

## Amendment 4 — 2026-10-06, after the development results: a nested tuning search (exploratory)

LightGBM stopped at 1–46 trees. An exploratory check, trees 1 to 300 with no
early stopping, showed training IC rising from 0.10 to 0.40 while validation and
test IC stayed at about 0.01 at every tree count. So stopping was not cutting off
signal. This search asks whether other settings, chosen properly, find more.

**Grid (162 settings):**
- num_leaves 4 / 15 / 63
- min_data_in_leaf 100 / 500 / 2,000
- lambda_l2 0 / 1 / 10
- learning_rate 0.01 / 0.03 / 0.1
- objective: regression on the ranked target, or **lambdarank**, with each day as a
  query and labels the day's fifths of y (0–4)
- the rest as registered: feature and bagging fractions 0.8, seed 7

**Nested selection, so the test block never chooses anything:**
1. Each setting is trained on each fold's training sessions for up to 1,000 trees.
2. The number of trees is the checkpoint (every 10) with the best mean daily IC on
   that fold's **validation** sessions.
3. The setting is the one with the best validation IC (at its best tree count),
   chosen **per fold**.
4. Only then is the chosen model scored on the fold's test block.

**Verdict:** the same criteria as the registered model, for signal and for the
spread paying at 6 bp. It is a second model after the first failed, so a pass
would also need to hold on the holdout. If it passes, the holdout runs once on the
setting chosen most often across folds, trained on all of development.

**Reported, no verdict:**
- which settings were chosen
- the test IC of every setting averaged over folds, to show how much the settings
  matter. That average is for information only and selects nothing.

**Status:** a first run was stopped at the user's request before any result was read.
It was rerun as registered, made resumable after a worker-threading slowdown, and
completed (1,134 fits).

### Amendment 4 — result

`python3 ml/tune.py`. Settings chosen per fold on validation IC:

| block | leaves | min_data | l2 | lr | objective | trees | valid IC | test IC |
|---|---|---|---|---|---|---|---|---|
| 0 | 4 | 2000 | 10 | 0.1 | regression | 10 | +0.074 | +0.029 |
| 1 | 4 | 500 | 1 | 0.03 | lambdarank | 40 | +0.102 | +0.009 |
| 2 | 15 | 500 | 0 | 0.03 | regression | 30 | +0.024 | +0.048 |
| 3 | 4 | 500 | 1 | 0.01 | lambdarank | 140 | +0.055 | +0.012 |
| 4 | 15 | 100 | 0 | 0.1 | regression | 520 | +0.032 | −0.018 |
| 5 | 63 | 100 | 1 | 0.03 | lambdarank | 10 | +0.019 | −0.007 |
| 6 | 15 | 100 | 10 | 0.03 | regression | 40 | +0.066 | −0.028 |

**The nested-tuned model has no signal and does not pay (fail on both):**
- IC +0.009 (t 0.95), positive in 4 of 7 blocks; against B1, +0.011 (t 0.89)
- spread +0.60 bp/day gross (t 0.19); net of 6 bp, −5.40 (t −1.74), 2 of 7 blocks positive

It is no better than the registered model (IC +0.011). The chosen setting changes
from fold to fold. Validation ICs of the chosen settings (+0.02 to +0.10) far exceed
their test ICs, the winner's curse of picking the best of 162.

**Information only:** test IC averaged over folds.
- The best settings are all 4-leaf regression trees (+0.016 to +0.019).
- The worst are fast lambdarank models (about −0.01).
- Across settings, mean validation IC and mean test IC correlate at +0.29.
- Even the best setting, chosen in hindsight, stays below atr_pct on its own
  (IC +0.026).

More capacity or tuning does not find more signal; the simplest models do best.
The holdout stays sealed.
