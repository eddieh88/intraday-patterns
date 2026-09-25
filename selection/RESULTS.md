# Results — the selection study

Registered in [`../prereg/selection.md`](../prereg/selection.md). Results are added
here in the order the steps run. Development data only; the holdout is sealed.

## Data

104,806 name-days with outcomes (30 under the 10bp floor, 9 with no complete
opening window and 57 missing a required bar were dropped). 98,014 complete
cases; 6,792 dropped for a missing feature. Out of sample: 66,349 name-days in
689 sessions, 2022-07 → 2025-03.

## Step 3 — descriptive (no verdict by design)

| target | out-of-sample R² | Spearman | slope, session-clustered t |
|---|---|---|---|
| **signed continuation `y`** — does the opening direction persist? | **−0.0013** | **+0.003** | +0.63 |
| **efficiency ratio** — is it a trend day, either way? | −0.0002 | +0.021 | **+2.22** |

**Direction: nothing.** The features do not predict whether the opening move
persists. In every fold the penalty chosen on the training set's own last six
months was the largest registered (α = 10,000) — the procedure preferring to
predict the mean. That sits at the edge of the registered grid; widening it now
would be a post-hoc change, and could only shrink predictions further toward the
mean.

**Trendiness: a faint signal.** Positive rank correlation in 4 of 6 blocks, t =
2.22 pooled, with the last block negative. This is the pattern anticipated at
registration — structure in magnitude, none in sign — but weak, and the pooled
R² is still slightly below zero.

Per block:

| block | n | α | R² (y) | Spearman (y) | R² (er) | Spearman (er) |
|---|---|---|---|---|---|---|
| 2022-07 | 12,214 | 10,000 | −0.0033 | −0.011 | −0.0019 | +0.008 |
| 2023-01 | 11,914 | 10,000 | −0.0004 | +0.009 | −0.0009 | +0.021 |
| 2023-07 | 12,032 | 10,000 | −0.0004 | +0.011 | +0.0006 | +0.025 |
| 2024-01 | 11,901 | 10,000 | −0.0026 | −0.008 | +0.0007 | +0.024 |
| 2024-07 | 12,415 | 10,000 | −0.0005 | +0.011 | +0.0025 | +0.052 |
| 2025-01 | 5,873 | 10,000 | +0.0000 | +0.007 | −0.0043 | −0.018 |

Largest standardised coefficients for `y` (mean over folds): opening range /
ATR −0.012, session after FOMC +0.012, room to next level +0.011, first-bar
share +0.011. Most keep their sign in 6 of 6 folds, but the folds use expanding
windows and share most of their training data, so that agreement is not
independent evidence. All are small.

## Step 4 — the gate, on the ridge predictions: FAIL, both gates

Ranked on predicted continuation. A gate passes only if, under both costs, the
top fifth's net R has a session-clustered 95% CI above zero and top minus
bottom has t > 1.96.

| gate | top fifth, cost (a) 3bp/1R | cost (b) 0.023R | gross | top − bottom t (a / b) |
|---|---|---|---|---|
| pooled | −0.020 [−0.054, +0.014] | −0.011 [−0.045, +0.023] | +0.012 | 0.22 / 0.46 |
| within-session | −0.015 [−0.038, +0.009] | −0.005 [−0.029, +0.018] | +0.018 | 0.75 / 1.15 |

Net R by quintile of prediction, pooled, cost (a): −0.024, −0.013, −0.031,
−0.029, −0.020 — not even ordered. Gross of costs the trade earns about +0.01R;
costs are 0.023–0.03R.

Exits: 77% at 11:00, 20% at the stop, 3% at the target. The pooled top fifth
spans 648 of 689 sessions, so it is not a handful of days.

**Registered reading: nothing → stop.** Ridge ends here. A pre-specified
nonlinear model is added below by amendment, at a stricter bar.

## Amendment 4 — LightGBM, fixed settings, bar 2.24: FAIL, both gates

**Step 3 form:**

| target | out-of-sample R² | Spearman | slope t |
|---|---|---|---|
| signed continuation `y` | −0.0000 | −0.011 | +0.08 |
| efficiency ratio | −0.0010 | −0.015 | −1.08 |

Early stopping, on each training set's own last six months, chose **1 to 9 trees
in most folds** against a cap of 2,000 — 75 and 233 in one fold each. The model
found nothing it could learn. What little it fitted leaned on session-wide
features (share of split gain for `y`: SPY alignment 54%, breadth 28%, SPY
volatility 7%), so its rankings mostly sort *days*, not names. The faint
trend-day signal ridge found does not survive (Spearman −0.015 against +0.021).

**Step 4 form:**

| gate | top fifth, cost (a) | cost (b) | top − bottom t (a / b) |
|---|---|---|---|
| pooled | −0.042 [−0.094, +0.010] | −0.034 [−0.086, +0.018] | −1.26 / −1.18 |
| within-session | −0.042 [−0.071, −0.014] | −0.030 [−0.059, −0.002] | −1.24 / −0.93 |

The best fifth is *worse* than the worst fifth. The pooled top fifth sits in
264 of 689 sessions — it is selecting days.

## Conclusion

**No.** Out of sample over 689 sessions, nothing visible at 09:45 — catalyst,
opening activity, market alignment, location, regime or calendar — identifies
the mornings on which a momentum entry pays after costs. Neither a linear model
nor a pre-specified nonlinear one ranks mornings better than chance, and the
momentum entry itself earns about +0.01R gross against 0.023–0.03R of cost.

This closes the study as registered. **The holdout (2025-04-01 onward) stays
sealed** — nothing here earned a look at it, so it remains clean for a future
question.

Deferred, as recorded in Amendment 3: CPI and NFP days, and earnings. They
would need their own registration, and the forward period as their clean test.
