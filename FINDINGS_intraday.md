# Step 5 result: the overshoot did not relocate, and timing decay is not the problem

Pre-registered in [`PREREG_intraday.md`](PREREG_intraday.md). One of its two
recorded predictions was wrong, which is the more useful half of this document.

## Test B — did the same-day overshoot move below daily frequency?

Cross-sectionally demeaned morning return (09:35–12:00) against afternoon return
(12:00–16:00), top 900 by dollar volume, 500 sample days:

| era | mean cross-sectional correlation | days | median names |
|---|---|---|---|
| 2002–2008 | −0.0051 | 139 | 848 |
| 2009–2016 | **−0.0772** | 145 | 877 |
| 2017–2026 | **+0.0219** | 200 | 894 |

Pre-registered verdict: **NOT INTRADAY** — the modern value is positive, and
weaker than 2002–2008 rather than stronger.

The overshoot did not hide below daily frequency. Intraday reversal peaked in
2009–2016 at −0.0772 and has **flipped sign**. Morning moves now continue into
the afternoon.

### The pattern is now consistent at every horizon we can measure

| measurement | early era | modern era |
|---|---|---|
| intraday, morning → afternoon | −0.0051 / −0.0772 | **+0.0219** |
| daily, lag 1, large moves | −0.0262 | **+0.0036** |
| daily, lag 1, all moves | −0.0269 | −0.0018 |

Three independent measurements at three timescales, one transition: **reversal
became continuation.** Prices that move keep moving, where they used to bounce.

That is a coherent account of everything in this project. The strategy was paid
to absorb temporary dislocations. Dislocations are no longer temporary — and at
the short horizons where they were largest, they now extend rather than correct.

## Test A — how much signal is lost between 15:45 and the close?

| era | cross-sectional SD of the 15:45→close move |
|---|---|
| 2002–2008 | 0.478% |
| 2009–2016 | 0.453% |
| 2017–2026 | 0.417% |

Against daily residual volatility of 2.08%, the final fifteen minutes carries
**20% of a day's cross-sectional dispersion in SD terms, 4% in variance**. A
signal computed at 15:45 is roughly **98% correlated** with one computed at the
close.

### A retraction

The pre-registration predicted "large decay for L=1, negligible for L=30". It is
negligible for both.

More importantly, this retracts a claim repeated several times earlier in the
project: that L=1 reversal "requires being positioned at close(t−1) on a signal
determined by close(t−1)" and is therefore structurally unexecutable regardless
of cost assumptions. **It is a 2% signal degradation.** L=1 died because large
moves now continue at lag 1 — a measured fact — not because of an execution
impossibility that was asserted and never measured.

The argument sounded right, was repeated as though established, and was wrong.
Measuring it cost one download and one script.

## Consequences

**The execution thesis narrows.** Of the three cost components — commission,
timing decay, fill quality — the first is known and the second is now measured
and small. Only fill quality and market impact remain, and those genuinely
require submitting real orders. The 1bp-versus-2bp question is still the highest
leverage unknown in the project, but the free half of it is answered, and the
answer is that this is not where the cost lives.

**One place the data would support a neural network.** The +0.0219 intraday
continuation is a real cross-sectional effect measured across ~894 names and 200
days. Intraday prediction is the first problem encountered in this project with
the observation count and signal-to-noise a network needs — unlike daily returns,
where every architecture tested landed within noise of a zero-parameter rule.

It also implies daily-or-faster rebalancing, and **turnover has killed every
result in this project without exception.** Any test of it needs its own
pre-registration, its own null, and a cost schedule fixed before the first run.
