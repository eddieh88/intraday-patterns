"""The Lunch Box simulator on hand-built days."""
import pandas as pd
import pytest

from paths import add_to_path
add_to_path("explore_nq")
import box

DAY = pd.Timestamp("2026-03-05")


def day(path):
    """12:00-15:00 at 1000. Box 12:00-12:30 = 990-1010 (h=20, 20 bp at 10000 is too wide,
    so the price is 20000). path: {minute offset from 12:30: (o, h, l, c)}"""
    ts = pd.date_range(DAY + pd.Timedelta("12:00:00"), DAY + pd.Timedelta("15:00:00"), freq="1min")
    df = pd.DataFrame({"open": 20000.0, "high": 20000.0, "low": 20000.0, "close": 20000.0}, index=ts)
    df.iloc[0, :] = [20000, 20010, 20000, 20000]
    df.iloc[1, :] = [20000, 20000, 19990, 20000]
    for k, v in path.items():
        df.iloc[30 + k, :] = v
    return df


def test_long_at_the_bottom_hits_its_target():
    # limit 19992, target 20002, stop 19985
    t = box.day_trades(DAY, day({2: (19995, 19995, 19991.5, 19994), 4: (19995, 20002.5, 19995, 20001)}))[0].iloc[0]
    assert (t.side, t.entry, t.why, t.pts) == (1, 19992.0, "target", 10.0)


def test_close_outside_the_box_exits_at_the_next_open():
    t = box.day_trades(DAY, day({2: (19995, 19995, 19991.5, 19994), 3: (19993, 19993, 19988, 19989),
                                 4: (19988, 19989, 19987, 19988)}))[0].iloc[0]
    assert (t.why, t.exit) == ("box break", 19988 - box.TICK)


def test_short_at_the_top_and_the_hard_stop():
    # short limit 20008, stop 20015
    t = box.day_trades(DAY, day({2: (20005, 20008.5, 20005, 20006), 3: (20006, 20016, 20006, 20009)}))[0].iloc[0]
    assert (t.side, t.why, t.pts) == (-1, "stop", -(20015 + box.TICK - 20008))


def test_wide_box_is_skipped_and_bias_blocks_the_other_side():
    wide = day({})
    wide.iloc[0, 1] = 20040
    assert box.day_trades(DAY, wide) == []
    assert box.day_trades(DAY, day({2: (19995, 19995, 19991.5, 19994)}), bias=-1) == []
