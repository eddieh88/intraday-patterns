# Experiments

Each file is one claim, one test. Run them **from the repository root**, since
they read `cache/` and `lib/` relative to it:

```bash
python3 experiments/e18_momentum.py
```

Results, corrections and limitations are in [`../FINDINGS.md`](../FINDINGS.md).

## The series

| file | claim under test | verdict |
|---|---|---|
| `e02_gap_fill.py` | Opening gaps fill in the same session | Size-dependent — 69% under 0.2%, 27% over 2% |
| `e03_judas.py` | The opening move is a false move (PO3 / judas) | Null — 50.5% vs a 50.0% coin flip |
| `e04_or_sweep.py` | The opening range is swept, then reverses | Refuted — breaks continue; fading loses 5.7 bp |
| `e05_premarket.py` | Pre-market sets the day's direction | Refuted — 49.2%, and the high-sweep rule inverts |
| `e06_intraday_retest.py` | Prior-day S/R break, then retest, pays | Negative — −0.073R |
| `e06b_level_stop.py` | …with the stop below the level instead | Negative — re-specified once, so exploratory |
| `e07_orb_build.py` | *(builds the daily table for E7)* | — |
| `e07_orb_test.py` | ORB on high relative-volume names | +0.009R; the prereg needed +0.05 |
| `e08_exits.py` | The exit rule is what decides it | Refuted — 7 policies within 0.04R, all negative |
| `e09_path.py` | *Descriptive:* what a trade does after entry | Losers peak bar 1–7, winners bar 40 |
| `e10_entries.py` | Structured entries beat a random bar | Superseded by e10b–e10f |
| `e10b_widestop.py` | …with a 2-bar stop, after the friction artifact | Superseded |
| `e10c_symmetric.py` | …run symmetrically, long and short | Superseded |
| `e10d_atrstop.py` | …with the literature-standard 2×ATR(14) stop | Superseded |
| `e10e_corrected.py` | …with the universe made point-in-time | Superseded |
| `e10f_gross.py` | …gross of costs, paired session-level inference | Superseded by e16–e18 |
| `e11_levels.py` | Reactions at marked levels differ from random prices | Null |
| `e12_fvg.py` | Fair value gaps fill at the published rates | **Replicates** — 78.7 / 68.4 / 46.1% |
| `e12b_fvg_filtered.py` | …with the displacement filter practitioners require | Same |
| `e13_bos_fvg.py` | Break of structure → FVG → tap entry | Negative — −0.109R vs random's −0.121R |
| `e15_layers.py` | The edge is in selection and execution, not the pattern | Selection: no ordering. Execution: attempt failed |
| `e16_matched.py` | Matched placebo — the design with no weighting problem | Supersedes every earlier estimand |
| `e16b_riskmatched.py` | …with the risk unit matched too | Same conclusion |
| `e17_close.py` | Direction and timing, separated | Direction positive; **timing zero** |
| **`e18_momentum.py`** | **The pattern beats a naive momentum rule** | **Refuted on all four entries** |

E1 has no script of its own — the opening-hour volatility and volume profile
comes from the daily table built by [`../data/build_daily.py`](../data/build_daily.py)
and is plotted by [`../render/render_experiments.py`](../render/render_experiments.py).
E14 was never run.

## Not in the numbered series

| file | |
|---|---|
| `break_retest_daily.py` | Break-and-retest on daily bars, from the CNN-imaging thread that preceded this one |
| `prereg_tests_ab.py` | The two pre-registered intraday tests carried over from the statarb work — see [`../prereg/findings_tests_ab.md`](../prereg/findings_tests_ab.md) |

## Reading order

If you only read three: `e17_close.py` separates direction from timing,
`e18_momentum.py` is the benchmark that settles it, and `e16_matched.py` is the
design that made both trustworthy.
