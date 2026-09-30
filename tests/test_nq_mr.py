"""The NQ mean-reversion simulator on hand-built days where the answer is known."""
import numpy as np
import pandas as pd
import pytest

from paths import add_to_path
add_to_path("explore_nq")
import mr

DAY = pd.Timestamp("2024-03-05")


def day_minutes(path):
    """1-minute bars from 10:03 to 12:00 at 100, with {minute offset from 10:03: (high, low)} overrides."""
    ts = pd.date_range(DAY + pd.Timedelta("10:03:00"), DAY + pd.Timedelta("12:00:00"), freq="1min")
    df = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0}, index=ts)
    for k, (h, l) in path.items():
        df.iloc[k, df.columns.get_loc("high")] = h
        df.iloc[k, df.columns.get_loc("low")] = l
    return df


def signal(close=100.0, high=104.0, low=98.0, atr=2.0, er=0.2):
    """One 3-minute signal candle, 10:00-10:03: limit at 98, target 101, stop 95."""
    return pd.DataFrame({"open": 101.0, "high": high, "low": low, "close": close, "er": er, "atr": atr},
                        index=[DAY + pd.Timedelta("10:00:00")])


def test_efficiency_ratio_trend_is_one_and_chop_is_zero():
    assert mr.efficiency_ratio(pd.Series(np.arange(20.0))).iloc[-1] == pytest.approx(1.0)
    assert mr.efficiency_ratio(pd.Series([0.0, 1.0] * 10)).iloc[-1] == pytest.approx(1 / 15)


def test_touching_the_limit_is_not_a_fill():
    assert mr.simulate(day_minutes({2: (100, 98.0)}), signal()).empty


def test_filters_block_trending_signals():
    assert mr.simulate(day_minutes({2: (100, 97.5)}), signal(er=0.5)).empty


def test_target_after_fill():
    t = mr.simulate(day_minutes({2: (100, 97.5), 4: (101.5, 99)}), signal()).iloc[0]
    assert (t.why, t.entry, t.pts) == ("target", 98.0, 3.0)
    assert t.pts_net == pytest.approx(3.0 - mr.COMMISSION)


def test_stop_beats_target_in_the_same_minute():
    t = mr.simulate(day_minutes({2: (100, 97.5), 4: (101.5, 94.0)}), signal()).iloc[0]
    assert (t.why, t.pts) == ("stop", 95.0 - mr.TICK - 98.0)


def test_no_target_in_the_fill_minute_unless_optimistic():
    m1 = day_minutes({2: (101.5, 97.5)})
    assert mr.simulate(m1, signal()).iloc[0].why == "time"
    assert mr.simulate(m1, signal(), optimistic=True).iloc[0].why == "target"


def test_time_stop_exits_at_the_open_15_minutes_after_the_fill():
    t = mr.simulate(day_minutes({2: (100, 97.5)}), signal()).iloc[0]
    assert t.exit_t == t.fill_t + pd.Timedelta("15min")
    assert t.pts == pytest.approx(100 - mr.TICK - 98)


def test_order_cancels_after_nine_minutes():
    assert mr.simulate(day_minutes({9: (100, 97.0)}), signal()).empty
    assert len(mr.simulate(day_minutes({8: (100, 97.0)}), signal())) == 1


def test_scale_in_adds_only_when_the_lower_limit_trades_through():
    lv = ((1.0, 0.5), (1.5, 0.5))                       # limits at 98 and 97
    one = mr.simulate(day_minutes({2: (100, 97.5), 4: (101.5, 99)}), signal(), levels=lv).iloc[0]
    two = mr.simulate(day_minutes({2: (100, 96.5), 4: (101.5, 99)}), signal(), levels=lv).iloc[0]
    assert (one.n_fills, one.pts) == (1, 0.5 * 3)
    assert (two.n_fills, two.pts) == (2, 0.5 * 3 + 0.5 * 4)


def test_clustered_se_matches_iid_with_singleton_clusters():
    x = np.array([1.0, 2.0, 4.0, 7.0])
    m, se = mr.clustered(x, np.arange(4))
    assert m == pytest.approx(x.mean())
    assert se == pytest.approx(x.std(ddof=1) / 2)


def test_mirror_turns_a_rip_into_a_long_dip():
    m1 = day_minutes({2: (102.5, 100)})                  # a spike up, no dip
    sig = signal(close=100.0, high=102.0, low=96.0)      # mirrored: limit at -102, target -99
    assert mr.simulate(m1, sig).empty
    t = mr.simulate(mr.mirror(m1), mr.mirror(sig).assign(er=0.2, atr=2.0)).iloc[0]
    assert (t.entry, t.why) == (-102.0, "time")


def test_target_in_atrs_from_the_limit():
    t = mr.simulate(day_minutes({2: (100, 97.5), 4: (99.5, 99)}), signal(), target_atr=0.5).iloc[0]
    assert (t.why, t.pts) == ("target", 1.0)
