import numpy as np

from r_multiple import PAD, RR, bracket


def _bars(highs, lows, closes):
    return (np.array(highs, float), np.array(lows, float), np.array(closes, float))


def test_target_hit_returns_rr():
    # entry at close 100, stop just under low 99; risk ~1.2, target ~103.6
    h, l, c = _bars([100, 101, 110], [99, 100, 105], [100, 100.5, 108])
    assert bracket(h, l, c, 0) == RR


def test_stop_counts_first_when_one_bar_spans_both():
    h, l, c = _bars([100, 110], [99, 90], [100, 100])
    assert bracket(h, l, c, 0) == -1.0


def test_no_barrier_marks_to_market_in_r():
    h, l, c = _bars([100, 100.5, 100.5], [99, 99.8, 99.8], [100, 100.2, 100.4])
    risk = 100 - 99 * (1 - PAD)
    assert np.isclose(bracket(h, l, c, 0, maxbars=2), (100.4 - 100) / risk)


def test_non_positive_risk_is_rejected():
    h, l, c = _bars([100, 101], [101, 100], [100, 100])
    assert bracket(h, l, c, 0) is None
