"""The holdout for prereg/selection.md, enforced in code.

Sessions from HOLDOUT_START onward are sealed until step 5. Any feature table,
model or result in that study must pass its dates through `development()` or
`assert_sealed()`. Reading the holdout requires setting
HOLDOUT_UNLOCK=final-evaluation in the environment, which is meant to happen
exactly once, and is recorded in the pre-registration when it does.
"""
import os
import pandas as pd

HOLDOUT_START = pd.Timestamp("2025-04-01")
_UNLOCKED = os.environ.get("HOLDOUT_UNLOCK") == "final-evaluation"

def development(df, col="date"):
    """Rows before the holdout. The default way to load data in this study."""
    return df[pd.to_datetime(df[col]) < HOLDOUT_START]

def assert_sealed(dates):
    """Fail loudly if any holdout date is present and the holdout is not unlocked."""
    d = pd.to_datetime(pd.Series(dates))
    n = int((d >= HOLDOUT_START).sum())
    if n and not _UNLOCKED:
        raise RuntimeError(
            f"{n} rows fall in the sealed holdout (>= {HOLDOUT_START.date()}). "
            "See prereg/selection.md; set HOLDOUT_UNLOCK=final-evaluation only for step 5.")
    return d
