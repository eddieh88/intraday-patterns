"""The silent-flip simulator on hand-built bars where the answer is known."""
import numpy as np
import pytest

import sys
from paths import add_to_path
add_to_path("flip")
sys.modules.pop("sim", None)          # stops/ and flip/ both have a sim.py
import sim

HH = 9.5 + np.arange(78) * 5 / 60          # 09:30 ... 15:55


def test_bars15_groups_three_five_minute_bars():
    o = np.arange(6.0); c = o + 0.5; h = o + 1; l = o - 1
    O, H, L, C, starts = sim.bars15(o, h, l, c, HH[:6])
    assert O.tolist() == [0, 3] and C.tolist() == [2.5, 5.5]
    assert H.tolist() == [3, 6] and L.tolist() == [-1, 2] and starts.tolist() == [0, 3]


def test_flip_high_is_the_latest_swing_above_yesterdays_high_from_before_yesterday():
    #            session 0                session 1 (day before)    session 2 (yesterday)
    H = np.array([10, 12, 15, 12, 10,      10, 11, 13, 11, 10,       10, 11, 12, 11, 10.])
    L = H - 1
    sess = np.repeat([0, 1, 2], 5)
    FH, FL = sim.flip_levels(H, L, sess, 2, RH=12.0, RL=8.5)
    assert FH == 13                       # session 1's swing, more recent than session 0's 15
    FH, _ = sim.flip_levels(H, L, sess, 2, RH=14.0, RL=8.5)
    assert FH == 15                       # only session 0's swing is above 14
    FH, _ = sim.flip_levels(H, L, sess, 2, RH=20.0, RL=8.5)
    assert np.isnan(FH)


def pattern_bars(c1=(100, 101.1, 99.9, 101.0), c2=(101.0, 101.2, 100.5, 100.6)):
    """15-minute O, H, L, C with a bullish candle 1 and a red candle 2, then filler."""
    rows = [c1, c2] + [(100.6, 100.7, 100.5, 100.6)] * 4
    O, H, L, C = (np.array(x, float) for x in zip(*rows))
    return O, H, L, C


def test_short_setup_at_the_range_high():
    O, H, L, C = pattern_bars()
    p = sim.pattern(O, H, L, C, atr=1.0, RH=101.2, RL=98.0, FH=103.0, FL=np.nan, sp=sim.PRIMARY)
    assert p["side"] == -1 and p["level"] == "RH"
    assert p["trig"] == 100.5                               # candle 2's low
    assert p["stop"] == pytest.approx(101.2 + 0.1)          # above both highs
    assert p["tgt"] == 98.0                                 # yesterday's low


def test_no_setup_when_candle_2_closes_green_or_candle_1_is_weak():
    O, H, L, C = pattern_bars(c2=(100.6, 101.0, 100.5, 100.9))
    assert sim.pattern(O, H, L, C, 1.0, 101.2, 98.0, np.nan, np.nan, sim.PRIMARY) is None
    O, H, L, C = pattern_bars(c1=(100, 100.8, 99.9, 100.7))                 # range 0.9 < 1 ATR
    assert sim.pattern(O, H, L, C, 1.0, 101.2, 98.0, np.nan, np.nan, sim.PRIMARY) is None


def test_no_setup_when_candle_1_does_not_reach_a_level():
    O, H, L, C = pattern_bars()
    assert sim.pattern(O, H, L, C, 1.0, 101.5, 98.0, np.nan, np.nan, sim.PRIMARY) is None   # 101.1 < 101.5 - 0.25


def test_execute_fills_on_the_trigger_and_hits_the_target():
    n = 78
    o = np.full(n, 100.8); h = o + 0.1; l = o - 0.1; c = o.copy()
    l[7] = 100.4                                           # 10:05 bar trades through 100.5
    o[8:] = 99; h[8:] = 99.2; l[8:] = 97.9; c[8:] = 99     # falls to the target next bar
    p = dict(side=-1, trig=100.5, stop=101.3, tgt=98.0)
    ex = sim.execute(o, h, l, c, HH, p)
    assert ex["j"] == 7 and ex["fill"] == 100.5 and ex["out"] == 1
    assert ex["R"] == pytest.approx((100.5 - 98.0) / 0.8)  # target filled at 98, below the 99 open
    assert ex["tgt_R"] == pytest.approx(2.5 / 0.8)


def test_execute_cancels_if_the_stop_trades_first_and_counts_a_stop_in_the_fill_bar():
    n = 78
    o = np.full(n, 100.8); h = o + 0.1; l = o - 0.1; c = o.copy()
    h[6] = 101.4                                           # 10:00 bar reaches the stop before any fill
    assert sim.execute(o, h, l, c, HH, dict(side=-1, trig=100.5, stop=101.3, tgt=98.0)) is None
    h[6] = 100.9; l[7] = 100.4; h[7] = 101.4               # fills and reaches the stop in one bar
    ex = sim.execute(o, h, l, c, HH, dict(side=-1, trig=100.5, stop=101.3, tgt=98.0))
    assert ex["out"] == 0 and ex["R"] == pytest.approx(-1.0)


def test_long_mirror_and_gap_fill_at_the_open():
    n = 78
    o = np.full(n, 99.2); h = o + 0.1; l = o - 0.1; c = o.copy()
    o[6] = 99.8; h[6] = 99.9; l[6] = 99.7; c[6] = 99.8     # 10:00 bar opens above the 99.5 trigger
    ex = sim.execute(o, h, l, c, HH, dict(side=1, trig=99.5, stop=98.7, tgt=102.0))
    assert ex["fill"] == 99.8 and ex["out"] == 2           # filled at the open, exits at the close
    assert ex["R"] == pytest.approx((99.2 - 99.8) / (99.8 - 98.7))


def test_trailing_stop_moves_to_break_even_after_one_r():
    n = 78
    o = np.full(n, 100.5); h = o + 0.05; l = o - 0.05; c = o.copy()
    l[6] = 100.45; o[6] = 100.6                            # fills at 100.5 in the 10:00 bar, stop 101.0
    o[7:9] = 99.9; h[7:9] = 100.0; l[7:9] = 99.4; c[7:9] = 99.5   # +1R reached by the 10:10 close
    o[9:] = 100.3; h[9:] = 100.7; l[9:] = 100.2; c[9:] = 100.6    # back up through the break-even stop at 100.5
    _, _, _, _, starts = sim.bars15(o, h, l, c, HH)
    R, out = sim.exits(o, h, l, c, 6, -1, 100.5, 101.0, 98.0, starts, trail=True)
    assert out == 0 and R == pytest.approx(0.0, abs=1e-9)
    R0, _ = sim.exits(o, h, l, c, 6, -1, 100.5, 101.0, 98.0)
    assert R0 == pytest.approx((100.5 - 100.6) / 0.5)      # without trailing it rides to the 100.6 close
