# Pre-registrations

Written before the data was touched, naming the statistic, the threshold and
what would falsify the idea. Recorded here whether or not the result was
flattering.

| file | status |
|---|---|
| `orb.md` | Run. E7 returned +0.009R against a +0.05 threshold. |
| `bos_fvg.md` | Run. E13 returned −0.109R against random's −0.121R. |
| `retest.md` | Run. **Not supported:** retests of real levels hold 50.2% of the time, fakes 50.3%; real − fake +0.24bp, 95% CI [−0.35, +0.84]. See `retest/RESULTS.md`. |
| `selection.md` | Run. **No** — nothing at 09:45 picks the mornings a momentum entry pays; see `selection/RESULTS.md`. Which name-days, visible at 09:45, make a pattern-free momentum entry pay after costs. Holdout enforced by `lib/holdout.py`. |
| **`nq_mean_reversion.md`** | **Registered, not yet run.** A long-only NQ 3-minute mean-reversion system posted on X, as published and with a scale-in; against random long entries. |
| **`ifvg.md`** | **Written, never run.** Inverse fair value gaps on futures, specified against expert review of the geometry. |

Only some of this project was pre-registered, and the rest is exploratory. That
distinction is kept explicit in [`../FINDINGS.md`](../FINDINGS.md) rather than
blurred after the fact — an earlier project here had to retract a +0.37 that
came from a hindsight parameter choice.
