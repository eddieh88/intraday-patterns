# selection

The name-day selection study, registered in [`../prereg/selection.md`](../prereg/selection.md).
Development data only; the holdout is sealed by [`../lib/holdout.py`](../lib/holdout.py).

| file | |
|---|---|
| `session_summary.py` | Stage A: one row per stock per session. Every field is tagged **known by 09:45** or **end of day, lagged use only**. |
| `features.py` | Stage B: the 09:45 feature table. |
| `test_audit.py` | The timestamp audit. **Must pass before step 3.** It scrambles what the features must not see and requires identical output, and it plants a leak to prove it can fail. |

Run from the repository root, in order:

```bash
python3 selection/session_summary.py   # ~4 min
python3 selection/features.py
python3 selection/test_audit.py
```

Status: features built and audited. **No outcome has been computed.** Step 3 is
next.
