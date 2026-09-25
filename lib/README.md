# lib

Shared detectors. Experiments add `lib/` to `sys.path` and import from here, so
every experiment sees the same definition of a level, a break and a retest.

| file | |
|---|---|
| `intraday_levels.py` | Prior-day and pre-market S/R, breaks and retests. Holds `MIN_GAP`, `MIN_ADV`, `RWIN` — the separation and advance rules that fixed the error where 73% of "retests" were the next bar. |
| `setups_v2.py` | Horizontal-level breaks and trendline breaks, analysed **separately** — conflating them was the earlier mistake. |
| `swing_levels.py` | Support/resistance from swing points, the way levels are actually drawn. |
| `r_multiple.py` | Evaluates setups as 1R:3R bracket trades rather than fixed-horizon returns. |

Changing anything here changes every experiment. `MIN_GAP` and `MIN_ADV` in
particular are judgement calls, documented in the definitions section of
[`../note/open-tests.html`](../note/open-tests.html).
