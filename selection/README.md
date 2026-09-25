# selection

The name-day selection study, registered in [`../prereg/selection.md`](../prereg/selection.md).
Development data only; the holdout is sealed by [`../lib/holdout.py`](../lib/holdout.py).

| file | |
|---|---|
| `session_summary.py` | Stage A: one row per stock per session. Every field is tagged **known by 09:45** or **end of day, lagged use only**. |
| `features.py` | Stage B: the 09:45 feature table. |
| `outcomes.py` | Targets and trade results — the only code that reads bars from 09:45 on. |
| `step3.py`, `step3_lgbm.py` | Walk-forward ridge, and the one pre-specified LightGBM model (Amendment 4). |
| `step4.py` | The registered gate: pooled and within-session, under both cost models. |
| `test_audit.py` | The timestamp audit. **Must pass before step 3.** It scrambles what the features must not see and requires identical output, and it plants a leak to prove it can fail. |

Run from the repository root, in order:

```bash
python3 selection/session_summary.py   # ~4 min
python3 selection/features.py
python3 selection/test_audit.py
```

**Result: no.** Nothing visible at 09:45 picks the mornings on which a momentum
entry pays, under a linear model or a pre-specified nonlinear one. The study
stopped at its registered gate and the holdout remains sealed. See
[RESULTS.md](RESULTS.md).
