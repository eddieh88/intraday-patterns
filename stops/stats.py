"""Session-clustered statistics and the prereg's cell definitions, shared by the checks."""
import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("stops")
import sim


def clustered(x, groups):
    """Mean, cluster-robust standard error and t, clustering by `groups` (sessions)."""
    x = np.asarray(x, float); g = np.asarray(groups)
    ok = np.isfinite(x); x, g = x[ok], g[ok]
    n = len(x)
    if n < 2:
        return np.nan, np.nan, np.nan, n
    m = x.mean()
    s = pd.Series(x - m).groupby(g).sum().values
    se = np.sqrt((s ** 2).sum()) / n
    return m, se, m / se if se > 0 else np.nan, n


def net(T, key, bp):
    """Net R of variant `key` at `bp` round-trip cost."""
    return T[f"R_{key}"] - bp * T[f"c_{key}"]


def cell(b, k):
    return f"{b}_{k}"
