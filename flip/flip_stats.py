"""Session-clustered statistics for the silent-flip checks."""
import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("flip")
import sim

BP = 3


def clustered(x, groups):
    """Mean, cluster-robust standard error, t and n of one sample."""
    x = np.asarray(x, float); g = np.asarray(groups)
    ok = np.isfinite(x); x, g = x[ok], g[ok]
    n = len(x)
    if n < 2:
        return np.nan, np.nan, np.nan, n
    m = x.mean()
    s = pd.Series(x - m).groupby(g).sum().values
    se = np.sqrt((s ** 2).sum()) / n
    return m, se, (m / se if se > 0 else np.nan), n


def clustered_diff(x, gx, y, gy):
    """Mean(x) - mean(y) for two unpaired samples, clustering both by session."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    okx, oky = np.isfinite(x), np.isfinite(y)
    x, gx, y, gy = x[okx], np.asarray(gx)[okx], y[oky], np.asarray(gy)[oky]
    if len(x) < 2 or len(y) < 2:
        return np.nan, np.nan, np.nan
    psi = pd.concat([pd.Series((x - x.mean()) / len(x), index=gx),
                     pd.Series(-(y - y.mean()) / len(y), index=gy)])
    se = np.sqrt((psi.groupby(level=0).sum() ** 2).sum())
    d = x.mean() - y.mean()
    return d, se, (d / se if se > 0 else np.nan)


def spec_mask(T, sp):
    return (T.strong == sp.strong) & (T.body == sp.body) & (T.tol == sp.tol) & (T.target == sp.target)


def net(x, col="R", cost="cost", bp=BP):
    return x[col] - bp * x[cost]
