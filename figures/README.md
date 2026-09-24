# figures

Regenerate rather than edit.

| file | script | shows |
|---|---|---|
| `E1_open_profile.png` | `render_experiments.py` | 5-min bar range and volume share by 30-min block |
| `E2_gap_fill.png` | " | gap fill rate by gap size; return to fading |
| `E3_po3.png` | " | 9:30-10:00 move vs 10:00-11:00 move, 20 bins; reversal rate by size |
| `E4_or_sweep.png` | " | % of opening-range breaks closing back inside; fade vs hold |
| `E5_premarket.png` | " | pre-market move vs opening move; the sweep-and-reverse rule |
| `E6a/E6b_retest.png` | " | R-multiple distribution, by level, outcome mix — two stop variants |
| `E7_orb.png` | " | mean R by relative-volume tier, by year, outcome distribution |
| `intraday_setups.png` | `render_intraday.py` | six real 5-min break-and-retest detections |
| `real_setups*.png` | `render_setups.py` | six real daily break-and-retest detections |

See `../INTRADAY_LOG.md` for what each experiment claimed, how it was measured,
and the limitations — only E7 was pre-registered, universes differ between
experiments, there is no holdout, and spread is assumed rather than measured.

Rendering is not decoration here. Looking at pictures caught three errors that
every statistical check passed: flat volume bars in simulated CNN images, a
missing moving-average line, and 73% of "retests" being the bar immediately
after the breakout.
