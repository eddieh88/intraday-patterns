"""Leak audit for the opening-hour ML features (prereg/opening_ml.md).

Everything a feature can see comes through opening(), etf_opening() or macro_at().
Changing every bar at or after each cutoff must leave them unchanged. The target
must change, or the test would prove nothing.
"""
import numpy as np
import pytest

from paths import add_to_path
add_to_path("ml")
import build

rng = np.random.default_rng(0)


def day5(pre=66, rth=78):
    hh = np.r_[4 + np.arange(pre) * 5 / 60, 9.5 + np.arange(rth) * 5 / 60]
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, len(hh))))
    o = np.r_[100, c[:-1]]
    h = np.maximum(o, c) * 1.001; l = np.minimum(o, c) * 0.999
    v = rng.integers(1_000, 50_000, len(hh)).astype(float)
    return o, h, l, c, v, hh


def scramble(arrs, hh, cut):
    out = [a.copy() for a in arrs]
    late = hh >= cut - 1e-9
    for a in out:
        a[late] = a[late] * rng.uniform(0.5, 2.0, late.sum())
    return out


def test_opening_ignores_bars_from_10_00():
    o, h, l, c, v, hh = day5()
    before = build.opening(o, h, l, c, v, hh)
    o2, h2, l2, c2, v2 = scramble([o, h, l, c, v], hh, 10.0)
    assert build.opening(o2, h2, l2, c2, v2, hh) == before
    assert build.target(o2, c2, hh) != pytest.approx(build.target(o, c, hh))   # the target does see them


def test_opening_uses_the_last_bar_before_10():
    o, h, l, c, v, hh = day5()
    op = build.opening(o, h, l, c, v, hh)
    assert op["c955"] == c[np.flatnonzero(np.isclose(hh, 9 + 55 / 60))[0]]
    assert op["o930"] == o[np.flatnonzero(np.isclose(hh, 9.5))[0]]


def test_etf_opening_ignores_bars_from_10_00():
    o, h, l, c, v, hh = day5()
    before = build.etf_opening(o, c, hh)
    o2, c2 = scramble([o, c], hh, 10.0)
    assert build.etf_opening(o2, c2, hh) == before


def test_macro_uses_bars_stamped_up_to_09_58_only():
    hh = np.arange(0, 24, 1 / 60)                          # one-minute futures bars, the whole day
    c = 100 + np.cumsum(rng.normal(0, 0.05, len(hh)))
    before = build.macro_at(hh, c, build.T_MACRO)
    (c2,) = scramble([c], hh, 9 + 59 / 60)
    assert build.macro_at(hh, c2, build.T_MACRO) == before
    assert before == c[np.flatnonzero(np.isclose(hh, 9 + 58 / 60))[0]]
