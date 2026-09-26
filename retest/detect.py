"""The retest detector for prereg/retest.md. Pure functions on bar arrays, so the
identical code scores simulated random walks and real sessions.

For one level on one session: find the first touch, require a move away, find
the retest, and score the move after each touch, signed so that positive means
the level held (price went back the way it came). The primary outcome runs from
the touching bar's close (Amendment 1).
"""
import numpy as np

AWAY, GAP, KS = 0.0018, 3, (6, 12)
FIRST_BY, RETEST_BY = 14.5, 15.0          # latest bar stamps, in hours
MERGE = 0.001

def score(c, prev_close, i, L, atr):
    """approach side from the close before bar i; bounce_k from the level price."""
    before = c[i - 1] if i > 0 else prev_close
    if not np.isfinite(before) or before == L: return None
    side = 1.0 if before > L else -1.0        # +1: came from above (falling into it)
    # a{k}: PRIMARY (Amendment 1) -- from the touching bar's close, a fixed time after the
    #       touch, so how the level was crossed cannot bias it.
    # b{k}: from the level price. Biased by crossing overshoot; reported as real - fake only.
    return ({f"a{k}": side * (c[i + k] - c[i]) / atr for k in KS} |
            {f"b{k}": side * (c[i + k] - L) / atr for k in KS} | {"from_above": side > 0})

def scan(o, h, l, c, hours, prev_close, L, atr):
    """-> (first, retest) records, either may be None."""
    n = len(c); last = max(KS)
    touch = (l <= L) & (h >= L)
    cand = np.flatnonzero(touch & (hours <= FIRST_BY))
    if not cand.size: return None, None
    i1 = cand[0]
    first = score(c, prev_close, i1, L, atr) if i1 + last < n else None
    far = np.maximum(h - L, L - l) >= AWAY * L
    away = np.flatnonzero(far[i1 + 1:])
    if not away.size: return first, None
    j = i1 + 1 + away[0]
    later = np.flatnonzero(touch[j + 1:]) + j + 1
    later = later[(later >= i1 + GAP) & (hours[later] <= RETEST_BY) & (later + last < n)]
    if not later.size: return first, None
    return first, score(c, prev_close, later[0], L, atr)

def levels(pdh, pdl, p2h, p2l, pmh, pml, open930):
    """real levels merged within 0.1% in registered order, and their mirrored fakes."""
    real = []
    for name, v in (("PDH", pdh), ("PDL", pdl), ("P2H", p2h), ("P2L", p2l), ("PMH", pmh), ("PML", pml)):
        if np.isfinite(v) and v > 0 and all(abs(v - r) > MERGE * r for _, r in real):
            real.append((name, v))
    fake = []
    for name, v in real:
        f = 2 * open930 - v
        if f > 0 and all(abs(f - r) > MERGE * r for _, r in real):
            fake.append((name, f))
    return real, fake
