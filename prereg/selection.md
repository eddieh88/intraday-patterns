# Pre-registration — selecting name-days for a momentum entry

Written 2026-09-25, **before any feature was built or any outcome of this design
measured.** Changes after this commit require a dated amendment at the bottom of
this file, made before the result they would affect is seen.

## The question

E18 showed that every setup's directional edge is plain momentum. So stop asking
which pattern works, and ask: **can conditions visible at 09:45 pick out the
name-days on which a momentum entry is profitable after costs?**

## What has already been seen

E1–E18 used the whole 2021–2026 sample, including the holdout below. The holdout
therefore protects the *feature search* in this study, not the momentum baseline,
which is already known. The only fully unseen data is what arrives after
2026-09-21 — see *The forward test*.

## Data

- **Universe:** each day's top 100 from `cache/intraday_pool.parquet` (point-in-time,
  prior 20 sessions of RTH dollar volume; guarded by `data/universe_check.py`).
- **Development:** 2021-01-19 → 2025-03-31, **1,055 sessions**.
- **Holdout:** 2025-04-01 → 2026-09-21, **370 sessions**. Enforced in code by
  `lib/holdout.py`; nothing in this study may read it until step 5.
- **Bars:** 5-minute, stamped at bar *start*. "The 09:30–09:45 window" is the
  bars stamped 09:30, 09:35, 09:40.

## The trade — one per name-day, fixed

| | |
|---|---|
| side | sign of (close of 09:40 bar − open of 09:30 bar). No trade if zero. |
| fill | **open of the 09:45 bar** — the first price available after the signal |
| risk unit, 1R | high − low of the 09:30–09:45 window (median 131bp) |
| stop / target | −1R / +2R from the fill, checked intrabar; stop assumed first on a tie |
| time exit | close of the 10:55 bar (11:00) |
| cost | 3bp round trip (0.023R at the median name-day); 6bp reported alongside |

The trade is deliberately pattern-free. Patterns may return later as features.

## Targets

- **Primary, for modelling — signed continuation:**
  `y = side × (close 10:55 − open 09:45) / 1R`. This is the direction-aware
  quantity a momentum entry is paid on. Targets may use data after the fill;
  features may not.
- **Secondary — efficiency ratio** of 09:45–11:00: |net move| / sum of |bar
  moves|. Sign-free. Used only to separate "features predict trend days" from
  "features predict the opening direction persists", which can come apart.
- **Economic outcome:** net R of the bracketed trade above.

Why not absolute move: in R units a bigger move with proportionally wider noise
leaves expected R unchanged. What pays is drift relative to noise, in the
entry's direction.

## Features — fixed list, all known by the close of the 09:40 bar

Scale is ATR14 of daily RTH ranges, computed through the prior day.

| family | feature |
|---|---|
| catalyst / in play | gap: (09:30 open − prior RTH close) / ATR |
| | pre-market dollar volume / its prior-20-day mean |
| | pre-market range / ATR |
| opening | 09:30–09:45 range / ATR |
| | 09:30–09:45 volume / its prior-20-day mean |
| | first-bar range / 09:30–09:45 range |
| | size of the signal move: \|close 09:40 − open 09:30\| / 1R |
| | body ratio of the window: \|close − open\| / (high − low) |
| market | SPY return 09:30–09:45, × side |
| | sector ETF return 09:30–09:45, × side. Sector ETF = the one of XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLB, XLRE, XLC, SMH most correlated with the stock over the prior 60 days |
| | residual move: stock return − beta × SPY return, 09:30–09:45, × side (beta from prior 60 days) |
| | breadth: share of the day's pool above their own 09:30 open at 09:45 |
| | VIXY return, prior close → 09:45 |
| regime | stock ATR14 / ATR100 |
| | SPY 20-day realised volatility |
| | 20-day return of the stock, × side |
| location | distance to prior-day high and to prior-day low, / ATR |
| | room to the next level in the trade direction, in R — nearest of PDH, PDL, pre-market high, pre-market low |
| | NR7 (yesterday's range narrowest of 7), inside day |
| name | log price; rank in the day's pool |
| calendar | day of week; month-end; monthly options expiration; FOMC, CPI and NFP days |

**Calendar dates** (FOMC, CPI, NFP) come from public schedules committed as a
file before step 3. If that file is not committed before step 3, these three are
dropped — decided now, not after seeing results.

**Earnings** are excluded. If a point-in-time earnings calendar is bought, it
enters by dated amendment before step 3, never after.

**Prior interactions**, the only ones allowed in step 3: gap × SPY-aligned,
opening relative volume × SPY-aligned, room-to-level × signal size.

Every feature gets a timestamp audit: a test that fails if its computation reads
any bar stamped 09:45 or later.

## Validation

Walk-forward over development only. Train on everything before a 6-month test
block, purge 2 sessions at the boundary, predict the block. Test blocks:
2022-07 → 2025-03 (five full blocks and one quarter), about **690 sessions** of
out-of-sample predictions. The first 18 months are training only.

Standard errors are clustered by session throughout.

## The steps, and where each can stop

**Step 3 — descriptive, no verdict.** Ridge regression on standardised features
for `y`, and separately for the efficiency ratio. Report out-of-sample R², and
coefficient signs and sizes. The question is whether features predict
*magnitude* (efficiency ratio), *direction persistence* (`y`), both or neither.

**Step 4 — the economic gate.** Pool the out-of-sample predictions of `y`, sort
name-days into quintiles, and measure each quintile's net R at 3bp.

- **PASS** if the top quintile's net R has a 95% session-clustered CI entirely
  above zero **and** top minus bottom is positive with t > 2.
- Otherwise **STOP**. Report the null. No boosting, no distillation, and the
  holdout stays sealed for a future question.

For calibration, not as a threshold: the top quintile holds about 13,800
name-days over ~690 sessions, giving an SE near 0.011R, so it must gross about
**0.045R** to pass at 3bp. The unconditional momentum entry in E18 grossed about
0.019R on a different risk unit — selection must roughly double it.

Also reported: within-session quintiles (removes day-level timing), and how
concentrated the top quintile is in a few sessions.

**Step 5 — only if step 4 passes.** Gradient boosting (shallow, heavily
regularised, monotone constraints only where this file states a prior),
walk-forward as above. Distil to a depth-2 or depth-3 tree read as two or three
rules. The rule must keep at least half the boosted model's top-quintile lift out
of sample, or it is too diffuse to trade as rules and the study reports that.

Then the holdout, **once**, on the distilled rule:

| verdict | holdout net R at 3bp |
|---|---|
| **WORKS** | > 0, session-clustered 95% CI excludes zero |
| **AMBIGUOUS** | > 0, CI includes zero |
| **DEAD** | ≤ 0 |

6bp reported alongside. The rule is not re-tuned after the holdout is read.

**Futures replication.** The distilled rule's day-level conditions, applied to ES
and NQ with the same entry, risk unit and exits, over the full sample. Reported
as a replication; no separate threshold. Run as soon as a rule exists, since
futures remove the spread-estimation problem.

## The forward test

The rule is evaluated again on the first six months of data after 2026-09-21,
fetched after this commit. That is the only test no part of this project has
touched.

## Known limitations, stated in advance

- **Effective sample** is ~1,055 sessions, not ~100,000 trades. Market-wide days
  move many names together.
- **Costs are flat.** A name- and time-varying spread cannot be estimated
  reliably from 5-minute OHLC at the open. Conditions that raise the edge (high
  volatility, low price) may also raise the true cost; this study cannot see
  that, which is one more reason for the futures replication.
- **The risk unit is one choice.** Whether a level should set the stop instead of
  the direction is a separate question for a separate registration.

## Amendments

### Amendment 1 — 2026-09-25, before any feature was built

Prompted by review. No outcome of this design had been measured.

**1. Two gates, not one.** Several features are identical for every name on a
given morning — SPY alignment, breadth, VIXY, the calendar. A pooled ranking can
therefore select *days* rather than *names*, which is index timing and far
cheaper to trade in futures. Step 4 now has two gates, each with the same test
(top-fifth net R, 95% session-clustered CI above zero, top minus bottom t > 2):

- **pooled:** top fifth of all out-of-sample name-days;
- **within-session:** top fifth of names inside each session, ranked on the
  prediction — about 20 per day.

| pooled | within-session | reading | next |
|---|---|---|---|
| pass | pass | stock selection | step 5 on stocks |
| pass | fail | **index timing** | step 5 on ES/NQ; the stock holdout stays sealed |
| fail | pass | relative selection only | step 5 as a within-day ranking rule |
| fail | fail | nothing | **stop** |

**2. Costs are charged per trade, under two models, and a gate must pass both.**
(a) 3bp of the fill price, divided by *that trade's own* 1R — so 0.06R on a
narrow 50bp range, 0.023R at the median. (b) A flat 0.023R per trade. Under (a) a
wide-range day really is cheaper in R, but true spreads may also widen on those
days, which a flat bp charge cannot see; (b) removes the link between range and
cost entirely. Passing both means the result does not come from the cost channel.
6bp is still reported alongside.

**3. VIXY stays a return, not a level** — roll decay makes its level drift for
years and would encode the date. VX futures levels are not used either: our
series is back-adjusted, so its level is not the true VIX.

**4. The timestamp audit asserts the bar convention itself.** Bars are stamped at
their *start*: regular hours are 09:30–15:55, 78 bars, verified on the data. The
audit fails if that stops holding, and fails if any feature reads a bar stamped
09:45 or later.

**5. Calendar features, now specified exactly:**
- FOMC decision day, and the session after it — `data/calendar/fomc_decisions.csv`,
  committed with this amendment;
- options expiration (third Friday, or the preceding session if closed) and
  month-end (last session of the month) — computed;
- CPI and NFP days — **still pending**. If their file is not committed before
  step 3, both are dropped, as the original registration says.

**6. Earnings will enter by amendment before step 3**, subject to: a
before-open / after-close flag on every event (an after-close report on day t is
the catalyst for session t+1); and a spot-check of at least 30 dates against
press releases, recorded here before use.

**7. Win rate is not reported as meaningful.** With a 131bp median risk unit, a
+2R target is rarely reached by 11:00, so most trades exit on time. The signed
continuation target already measures that exit.

### Amendment 2 — 2026-09-25, features built, no outcome computed

Implementation choices the registration left open, fixed here before any target
or trade result exists.

- **Body ratio is dropped.** |close − open| / (high − low) over the window is the
  signal size by construction, since 1R is the window's high − low.
- **Room to the next level** is capped at 10R when no level lies ahead, and is
  missing when none of the four levels is known.
- **Minimum history:** ATR14 10 sessions, ATR100 50, 20-day means 10, 60-day beta
  and sector correlation 40, SPY 20-day volatility 15.
- **Sector ETF:** the highest correlation of daily close-to-close returns over the
  prior 60 sessions, among the twelve listed.
- **The window is exact.** Window fields are missing unless all three bars
  (09:30, 09:35, 09:40) exist.
- **Early closes are detected, not listed.** On a session where under 20% of the
  09:30–16:00 volume trades after 13:00, the session ends at 13:00; otherwise
  after-hours prints enter the day's close and range. Every half day in 2021–26
  sits at ≤ 0.13 and every full day at ≥ 0.34. Only end-of-day fields, which are
  used lagged, depend on this.
- **Complete cases.** 93.5% of the 104,902 development name-days have every
  feature. Step 3 uses complete cases only and reports how many were dropped.

**The audit** (`selection/test_audit.py`) passes, and must pass before step 3:

| check | result |
|---|---|
| bar convention, including a known half day | pass |
| scrambling every bar from 09:45 on leaves all same-day fields unchanged | pass, 3 sessions |
| replacing a day's end-of-day fields and all later data with noise leaves that day's features unchanged | pass, 6 dates |
| **the audit can fail:** removing one `.shift(1)` is caught | caught on 6/6 dates, 6 features flagged |
| holdout sealed | last date 2025-03-31 |

### Amendment 3 — 2026-09-25, before any outcome was computed

**Dropped from this study, deferred to a later one: CPI and NFP days, and
earnings.** Neither data source is in hand. Both are to be looked into later,
but not added to this study after step 3 — that would be choosing features with
the results visible. A follow-up that uses them needs its own registration, and
since this study's holdout may by then have been read, its clean test is the
forward period (data after 2026-09-21).

**How outcomes are built from bars** (`selection/outcomes.py`):

- A name-day needs the 09:45 bar and the 10:55 bar; otherwise it is dropped and
  counted.
- Name-days with 1R under 10bp are dropped — 30 of 104,902, degenerate windows
  where any cost in R explodes.
- The bracket is checked on each bar from 09:45 through 10:55. A stop or target
  gapped through fills at the bar's open, as in E6–E18. Stop first on a tie.
- `y` = side × (10:55 close − 09:45 open) / 1R — the unbracketed trade.
- Efficiency ratio = |10:55 close − 09:45 open| / sum of |bar-to-bar close
  changes|, the first change measured from the 09:45 open.
- Net R: (a) 3bp × fill ÷ that trade's 1R; (b) a flat 0.023R; 6bp under (a) also
  reported.

**Step 3 in detail:**

- Features: the registered list less the dropped items; day of week as four
  dummies; the three registered interactions. Each fold winsorises every
  feature at its *training* 1st/99th percentiles, then standardises with
  training mean and SD.
- `y` and the efficiency ratio are winsorised at the training 1st/99th
  percentiles for fitting and for R². `y` has heavy tails, because a narrow
  window makes 1R small.
- Ridge penalty: chosen inside each training set only — fit on all but its last
  six months, score on those six months, over α ∈ {1, 10, 100, 1,000, 10,000};
  then refit on the full training set with the chosen α.
- Reported: pooled and per-block out-of-sample R², measured against the training
  mean; Spearman rank correlation of prediction with outcome; the slope of the
  outcome on the prediction with session-clustered t; and coefficient signs,
  sizes and sign-consistency across folds.
- Step 4 ranks on these same ridge predictions of `y`.

### Amendment 4 — 2026-09-25, after step 4 failed on ridge

**This amendment is made with step 3 and step 4 results visible**, and is marked
as such. The registered study stopped at step 4. This adds one pre-specified
second model, because a linear model cannot represent threshold effects of the
kind traders describe ("continuation only when the gap is large *and* SPY
agrees"), so a ridge null is not a null for every model.

To keep this from becoming a search:

- **One model, settings fixed here, never tuned on test blocks.** LightGBM,
  L2 regression on the same winsorised `y`: `max_depth` 3, `num_leaves` 7,
  `learning_rate` 0.02, `min_child_samples` 500, `feature_fraction` 0.8,
  `bagging_fraction` 0.8 every iteration, `lambda_l2` 10, seed 0. The number of
  trees is set by early stopping (patience 100, cap 2,000) on each training
  set's own last six months, then refit on the full training set with that
  number. Raw features — trees need no scaling — and no monotone constraints,
  since this file states no priors.
- **Everything else identical:** walk-forward blocks, purge, complete cases,
  both targets reported as in step 3, both gates and both cost models as in
  step 4.
- **A stricter bar.** This is the second model tried, so the gate's critical
  value is Bonferroni over two looks: **2.24** (97.5% two-sided) in place of
  1.96, for both the confidence interval and the top-minus-bottom t.
- **No third model.** If LightGBM fails, the study reports that neither a linear
  nor a pre-specified nonlinear model finds the effect, and stops. The holdout
  stays sealed.
- If it passes, step 5 proceeds on the LightGBM predictions as registered.
