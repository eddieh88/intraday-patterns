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
