# Results — does a level hold on the retest?

Registered in [`../prereg/retest.md`](../prereg/retest.md). Development period
only (2021-01-19 → 2025-03-31, 1,055 sessions); the holdout was not read.

## The random-walk check came first, and changed the outcome

On simulated random walks the registered outcome — scored from the level price —
showed a mechanical pass-through, and the fake-level control did not cancel it:
at coarse resolution real minus fake "passed" on pure noise (t = 2.23). The
primary outcome was moved, by Amendment 1 and before any real data, to the move
after the touching bar's close, which is unbiased at any resolution. The check
passes on it.

## Primary: NOT SUPPORTED

Retests; move over the 60 minutes after the touching bar's close, in ATR units,
positive when price went back the way it came (the level held):

| | retests | held | mean |
|---|---|---|---|
| real levels | 186,781 | 50.2% | +0.0007 (t +0.58) |
| fake levels | 141,282 | 50.3% | −0.0001 (t −0.11) |
| **real − fake** | | | **+0.0008, t = 0.86** |

In price: median ATR14 is 303bp, so real minus fake is **+0.24bp**, 95% CI
**[−0.35, +0.84]bp** over the hour. A precise zero: if levels hold on the retest,
the effect is under a basis point, against 3–6bp of cost.

## Secondary (no verdict)

| | real − fake | t |
|---|---|---|
| 30 minutes instead of 60 | −0.0003 | −0.41 |
| share held | −0.1 pp | −0.55 |
| from the level price (biased; see Amendment 1) | +0.0013 | +1.29 |
| support (falling into it) | +0.0001 | +0.11 |
| resistance (rising into it) | +0.0015 | +1.09 |

By level type, none clears the Bonferroni bar of |t| > 2.64: prior-day high
+0.32, prior-day low −1.23, two-days-back high −0.79, two-days-back low +0.89,
pre-market high +0.87, pre-market low +1.42.

**Does testing strengthen a level?** First touches: real − fake −0.0016
(t −1.31). Retest minus first touch, each net of its fake: +0.0025 (t 1.58). No.

## Conclusion

Price bounces off a previously touched level exactly as often as it bounces off
an arbitrary price the same distance from the open — about half the time. This
holds for every level type, from either side, and on first touches as on
retests. The holdout stays sealed.

**Not tested:** intraday swing highs and lows, round numbers, multi-week levels,
and anything inside the touching bar itself.
