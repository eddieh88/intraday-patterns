"""The structural-stop simulator on hand-built bars where the answer is known."""
import numpy as np
import pytest

from paths import add_to_path
add_to_path("stops")
import sim


def bars(*hl, o=None):
    """Bars from (high, low) pairs; open = the previous bar's midpoint unless given."""
    H = np.array([x[0] for x in hl], float); L = np.array([x[1] for x in hl], float)
    O = np.array(o, float) if o is not None else (H + L) / 2
    return O, H, L


# ---------- simulate ----------

def test_long_stop_first_target_and_time_exit():
    O, H, L = bars((101, 99.5), (102.5, 100.5), (101, 100), o=[100, 101, 100.5])
    R, out = sim.simulate(O, H, L, 100.8, 100.0, [True] * 3, [99.0, 99.6, 98.0], [102.0, 101.0, 104.0])
    assert out.tolist() == [1, 3, 2]                       # target, stop (bar 0 also reached 101), time
    assert R[0] == pytest.approx(2.0)                      # (102 - 100) / 1
    assert R[1] == pytest.approx(-1.0)                     # stop 99.6 hit by bar 0's low 99.5
    assert R[2] == pytest.approx(0.8 / 2.0)                # closes at 100.8, risk 2


def test_bar_spanning_both_barriers_counts_the_stop():
    O, H, L = bars((103, 98), o=[100])
    R, out = sim.simulate(O, H, L, 100, 100.0, [True], [99.0], [102.0])
    assert out[0] == 3 and R[0] == pytest.approx(-1.0)                # flagged as ambiguous


def test_gap_through_the_stop_fills_at_the_open():
    O, H, L = bars((100.5, 99.5), (97.5, 96.0), o=[100, 97])
    R, _ = sim.simulate(O, H, L, 97, 100.0, [True], [99.0], [102.0])
    assert R[0] == pytest.approx(-3.0)                     # filled at 97, not 99


def test_short_mirrors_long():
    O, H, L = bars((100.5, 97.5), o=[100])
    R, out = sim.simulate(O, H, L, 98, 100.0, [False], [101.0], [98.0])
    assert out[0] == 1 and R[0] == pytest.approx(2.0)


def test_stop_on_the_wrong_side_or_too_tight_is_nan():
    O, H, L = bars((101, 99), o=[100])
    R, _ = sim.simulate(O, H, L, 100, 100.0, [True, True], [100.5, 99.999], [102, 100.01])
    assert np.isnan(R).all()


# ---------- structural stops ----------

def test_orb_and_level_stops():
    h = np.array([101, 102, 103.0]); l = np.array([99, 100, 101.0]); c = np.array([100, 101, 102.0])
    v = np.full(3, 100.0)
    args = dict(h=h, l=l, c=c, vwap=v, orh=101.5, orl=99.2, pmh=101.4, pml=98.0, b=0.1)
    assert sim.structural_stop("ORB", True, 2, **args) == pytest.approx(99.1)
    assert sim.structural_stop("ORB", False, 2, **args) == pytest.approx(101.6)
    assert sim.structural_stop("level", True, 2, **args) == pytest.approx(101.0 - 0.1)   # retest low under the level
    assert sim.structural_stop("level", True, 1, **args) == pytest.approx(100.0 - 0.1)


def test_vwap_stop_is_the_low_of_the_dip_it_reclaimed():
    c = np.array([101, 99.5, 99.0, 99.6, 100.5]); h = c + 0.3; l = c - 0.3
    l[2] = 98.4                                           # the bottom of the dip
    v = np.full(5, 100.0)
    st = sim.structural_stop("VWAP", True, 4, h, l, c, v, 0, 0, 0, 0, 0.0)
    assert st == pytest.approx(98.4)


def test_pullback_stop_is_the_low_since_the_high():
    h = np.array([100.5, 101.0, 101.6, 101.3, 101.2]); l = np.array([100, 100.6, 100.4, 100.9, 100.8])
    c = np.array([100.4, 100.9, 101.4, 101.0, 100.9])
    st = sim.structural_stop("pullback", True, 4, h, l, c, c, 0, 0, 0, 0, 0.05)
    assert st == pytest.approx(100.8 - 0.05)               # bar 2's own low (100.4) is not counted


# ---------- signals and ATR ----------

def flat_day(n=60, p=100.0):
    hh = 9.5 + np.arange(n) * 5 / 60
    o = np.full(n, p); c = np.full(n, p); h = c + 0.1; l = c - 0.1
    return o, h, l, c, np.full(n, 1000.0), hh


def test_orb_fires_on_the_first_close_above_the_range_after_10():
    o, h, l, c, v, hh = flat_day()
    c[8] = h[8] = 100.5; o[9] = 100.5                      # 10:10 bar closes above 100.1
    sig = sim.signals(o, h, l, c, hh, c.copy(), np.nan, np.nan)
    assert ("ORB", True, 8) in sig
    assert not any(s == "ORB" and not up for s, up, _ in sig)


def test_atr_uses_the_prior_session_at_the_open():
    ranges = np.r_[np.full(14, 2.0), np.full(10, 1.0)]
    assert sim.atr_at(ranges, 14, 0) == pytest.approx(2.0)
    assert sim.atr_at(ranges, 14, 7) == pytest.approx((7 * 2 + 7 * 1) / 14)
    assert np.isnan(sim.atr_at(np.full(5, 1.0), 0, 3))


# ---------- the control ----------

def test_control_borrows_another_trades_width():
    def trade(w):
        n = 70
        return dict(setup="ORB", up=True, e=0, t=10.0, fill=100.0, atr=1.0,
                    O=np.full(n, 100.0), H=np.full(n, 100.05), L=np.full(n, 99.95), c_last=100.0,
                    stops={b: 100.0 - w for b in sim.BUFFERS}, widths={b: w for b in sim.BUFFERS},
                    v_stop=99.0, mom=1.0, orb_mid=99.5, lvl_tgts=(np.nan, np.nan))
    rows = sim.score_month([trade(1.0), trade(0.5)], np.random.default_rng(0))
    # Nothing moves, so every variant exits on time at 0R; the cost per bp tells the widths apart.
    assert rows[0]["c_S_0.1_2.0"] == pytest.approx(1e-4 * 100 / 1.0)
    assert rows[0]["c_C_0.1_2.0"] == pytest.approx(1e-4 * 100 / 0.5)   # trade 1's width
    assert rows[1]["c_C_0.1_2.0"] == pytest.approx(1e-4 * 100 / 1.0)
    assert rows[0]["n_C_0.1_2.0"] == sim.N_DRAWS
    assert rows[0]["R_S_0.1_2.0"] == pytest.approx(0.0)
