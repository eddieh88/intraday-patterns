"""The night-scalper simulator on hand-built nights."""
import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("explore_fx")
import night

T0 = pd.Timestamp("2024-03-04 16:00")        # a Monday afternoon; the night starts at 18:15


def path(spike_at, spike, after):
    """1-minute prices, flat at 1.0000 from 16:00 to 03:00; a spike at a minute offset,
    then `after` (later prices, the last one held to the end)."""
    ts = pd.date_range(T0, T0 + pd.Timedelta("11h"), freq="1min")
    p = np.full(len(ts), 1.0)
    p[spike_at] = spike
    for k, v in enumerate(after):
        p[spike_at + 1 + k] = v
    p[spike_at + len(after):] = after[-1]
    return pd.Series(p, index=ts)


def test_fade_a_spike_down_hits_the_middle_band():
    k = 150 + 4                                # 18:34, the last minute of the 18:30 bar
    t = night.simulate(path(k, 0.9990, [0.9991, 0.9995, 1.0001]))
    r = t.iloc[0]
    assert (r.side, r.why) == (1, "target")
    assert r.entry == 0.9991 and r.gross_bp > 0


def test_no_entries_in_the_afternoon():
    assert night.simulate(path(60, 0.9990, [0.9991, 1.0])).empty      # 17:00


def test_stop_is_twice_the_distance_to_target():
    k = 154
    t = night.simulate(path(k, 0.9990, [0.9991, 0.9960])).iloc[0]
    assert t.why == "stop"
    assert abs((t.target - t.entry) * 2 - (t.entry - t.stop)) < 1e-12


def test_flat_at_two_new_york():
    k = 154
    t = night.simulate(path(k, 0.9990, [0.9991])).iloc[0]
    assert t.why == "time" and t.t_out == pd.Timestamp("2024-03-05 02:00")


def test_cross_uses_only_minutes_where_both_legs_traded():
    a = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=pd.date_range("2024-01-01", periods=3, freq="1min"))
    b = pd.DataFrame({"close": [1.0, 1.0]}, index=a.index[[0, 2]])
    assert list(night.cross(a, b).index) == list(a.index[[0, 2]])
