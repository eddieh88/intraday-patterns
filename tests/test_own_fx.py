"""The spot-FX strategy simulators on hand-built bid/ask minutes."""
import numpy as np
import pandas as pd

from paths import add_to_path
add_to_path("explore_own")
import strategies as st


def frame(ts, mid, spread=0.0002, spread_pips=2.0):
    mid = np.asarray(mid, float)
    d = pd.DataFrame(index=pd.DatetimeIndex(ts))
    for side, sgn in (("bid", -1), ("ask", 1)):
        for c in ("open", "high", "low", "close"):
            d[f"{side}_{c}"] = mid + sgn * spread / 2
    for c in ("open", "high", "low", "close"):
        d[f"mid_{c}"] = mid
    d["spread_mean"] = spread_pips
    d["spread_max"] = spread_pips
    d["ticks"] = 10
    return d


def test_gap_fade_pays_the_spread_and_hits_target():
    fri = pd.date_range("2024-03-01 16:00", "2024-03-01 16:59", freq="1min")
    sun = pd.date_range("2024-03-03 17:00", "2024-03-04 17:00", freq="1min")
    mid = np.r_[np.full(len(fri), 1.0000), np.full(len(sun), 1.0050)]      # +0.5% gap up
    mid[len(fri) + 40:] = 1.0005                                           # fills back down
    t = st.gap(frame(fri.append(sun), mid), x=0.2, s=0.4, rr=1.0, wait=30).iloc[0]
    assert (t.side, t.why) == (-1, "target")
    assert abs(t.bp - 40) < 1                                             # 0.4% target, entry at bid


def test_gap_skips_small_gaps_and_wide_spreads():
    fri = pd.date_range("2024-03-01 16:00", "2024-03-01 16:59", freq="1min")
    sun = pd.date_range("2024-03-03 17:00", "2024-03-04 17:00", freq="1min")
    mid = np.r_[np.full(len(fri), 1.0), np.full(len(sun), 1.001)]
    assert st.gap(frame(fri.append(sun), mid), x=0.2).empty
    mid[len(fri):] = 1.005
    assert st.gap(frame(fri.append(sun), mid, spread_pips=9.0), x=0.2, cap=5.0).empty


def test_spread_filter_rejects_a_spike_above_its_4_minute_average():
    d = frame(pd.date_range("2024-03-04 20:00", periods=6, freq="1min"), np.ones(6))
    d["spread_mean"] = [1.0, 1.0, 1.0, 1.0, 1.8, 1.0]
    assert list(st.spread_ok(d, cap=2.0)) == [True, True, True, True, False, True]


def test_night_bracket_is_symmetric():
    ts = pd.date_range("2024-03-04 18:00", "2024-03-05 03:00", freq="1min")
    mid = np.full(len(ts), 1.0)
    k = ts.get_loc(pd.Timestamp("2024-03-04 20:34"))
    mid[k] = 0.9990                                  # the 20:30 bar closes far below its band
    mid[k + 1:k + 4] = 0.9991
    mid[k + 4:] = 1.0002                             # rebounds past the 1:1 target
    t = st.night(frame(ts, mid, spread=0.00002), exit="bracket").iloc[0]
    assert (t.side, t.why) == (1, "target")
