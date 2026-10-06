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
