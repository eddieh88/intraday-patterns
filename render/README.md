# render

Figure generation. Run from the repository root; output lands in `figures/`.

| file | |
|---|---|
| `render_experiments.py` | One figure per experiment from the cached tables → `figures/E1..E7_*.png` |
| `render_setups.py` | Real detected setups, so the detector can be checked by eye |
| `render_intraday.py` | Intraday setups in context |
| `render_twoday.py` | Two-day view: where the level comes from, and how it is acted on |

These are not decoration. **Rendering six real detections is what caught the
error where 73% of "retests" were the bar immediately after the breakout** — no
summary statistic showed it. Look at the charts before trusting a detector.
