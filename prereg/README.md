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
| `nq_mean_reversion.md` | Run. **Fails** on both periods: a long-only NQ 3-minute mean-reversion system posted on X makes −0.72 pts/trade in development and +1.05 (t 0.8) in the holdout, and the scale-in makes no difference to the mean. |
| `nq_lunch_box.md` | Run. **Fails** on both periods: fading the edges of a narrow 12:00–12:30 NQ box loses −2.27 pts/trade in development (t −3.4) and −0.17 in the holdout. Adding either the trend bias or the ES exit makes no difference. |
| `fx_distance_fade.md` | Run. **Not confirmed:** fading a fixed 1% distance from the 4-hour SMA(20) on six currency futures was the best of 63 one-rule variants in development (+0.31 ATR/trade, t 2.15). The holdout has the same sign but is within noise (+0.24, t 0.72). |
| `fx_night_scalper.md` | Run. **Fails** on both periods: an Asian-session Bollinger fade on three FX crosses makes +0.6 bp gross but −1.6 bp net in development (−1.9 in the holdout). It only breaks even at costs under ~0.6 bp. |
| **`ifvg.md`** | **Written, never run.** Inverse fair value gaps on futures, specified against expert review of the geometry. |

Only some of this project was pre-registered, and the rest is exploratory. That
distinction is kept explicit in [`../FINDINGS.md`](../FINDINGS.md) rather than
blurred after the fact — an earlier project here had to retract a +0.37 that
came from a hindsight parameter choice.
