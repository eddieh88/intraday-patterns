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


def _bars(mids, spread=0.0002):
    import generator as g
    ts = pd.date_range("2024-03-04 00:00", periods=len(mids), freq="1h")      # a Monday
    h = pd.DataFrame(index=ts)
    for c, v in zip(("open", "high", "low", "close"), np.array(mids, float).T):
        h[f"mid_{c}"] = v
        h[f"bid_{c}"] = v - spread / 2
        h[f"ask_{c}"] = v + spread / 2
    A = g.prepare(h)
    A["atr"] = np.full(len(h), 0.0010)
    A["month"] = np.zeros(len(h), np.int64)
    return g, A


def _run(g, A, go_l, a=1.0, b=1.0, hold=4):
    out = np.zeros((1, 3))
    g.run_one(np.array(go_l), np.zeros(len(go_l), bool), A["atr"], A["bo"], A["bh"], A["bl"], A["bc"],
              A["ao"], A["ah"], A["al"], A["ac"], A["mid_o"], A["ok"], A["fri_end"], A["month"], a, b, hold, out)
    return out[0]


def test_engine_long_hits_target_after_paying_the_spread():
    add_to_path("explore_own")
    # (open, high, low, close) mids: enter at bar 1's ask (1.0001), target +10 pips on the bid
    g, A = _bars([(1, 1, 1, 1), (1, 1, 1, 1), (1, 1.0013, 1, 1.0012), (1.0012,) * 4, (1.0012,) * 4, (1.0012,) * 4])
    s, n, _ = _run(g, A, [True, False, False, False, False, False])
    assert n == 1 and abs(s - 10.0) < 1e-6          # exit at target 1.0011 on the bid: +10 bp


def test_engine_stop_first_and_time_exit():
    add_to_path("explore_own")
    g, A = _bars([(1, 1, 1, 1), (1, 1, 1, 1), (1, 1.002, 0.998, 1), (1,) * 4, (1,) * 4, (1,) * 4, (1,) * 4])
    s, n, _ = _run(g, A, [True] + [False] * 6)
    assert n == 1 and abs(s - (1.0001 - 0.0010 - 1.0001) / 1.0 * 1e4) < 1e-6     # stop, not target
    g, A = _bars([(1,) * 4] * 8)
    s, n, _ = _run(g, A, [True] + [False] * 7, hold=3)
    assert n == 1 and abs(s - (-2.0)) < 1e-6        # time exit at the bid: pays the 2 bp spread


def test_shuffled_keeps_length_and_spreads():
    add_to_path("explore_own")
    import generator as g
    ts = pd.date_range("2024-03-04", periods=300, freq="1h")
    rng = np.random.default_rng(0)
    mid = 1 + np.cumsum(rng.normal(0, 1e-4, 300))
    h = pd.DataFrame({"mid_open": mid, "mid_high": mid + 1e-4, "mid_low": mid - 1e-4, "mid_close": mid}, index=ts)
    for c in ("open", "high", "low", "close"):
        h[f"bid_{c}"], h[f"ask_{c}"] = h[f"mid_{c}"] - 1e-5, h[f"mid_{c}"] + 1e-5
    n = g.shuffled(h, 1)
    assert len(n) == 300 and (n.mid_low <= n.mid_high).all()
    assert np.allclose(n.ask_open - n.bid_open, 2e-5)
