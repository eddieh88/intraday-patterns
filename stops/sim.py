"""Structural stops for the four E17 entries. Rules: prereg/structure_stops.md.

Pure functions on one session's arrays, so the same code runs on real bars
(run.py), on random walks (random_walk_check.py) and on hand-built days (tests).

  signals()          E17's entries, verbatim
  structural_stop()  the stop at the setup's own structure, long or short
  simulate()         bracket trades from the open of bar e+1, many variants at once
  session_trades()   phase 1: every entry in a session, with what phase 2 needs
  score_month()      phase 2: width-matched control draws, then every variant
"""
import numpy as np

CAP, MAXB, MIN_RISK = 3, 60, 0.0003
BUFFERS = (0.0, 0.1, 0.25)           # x ATR
TARGETS = (2.0, 3.0)                 # R
PRIMARY_B, PRIMARY_T = 0.1, 2.0
N_DRAWS, SEED = 20, 7
ATR_N, MOM_K = 14, 6
SETUPS = ("ORB", "level", "VWAP", "pullback")


def signals(o, h, l, c, hh, vwap, pmh, pml):
    """E17's four entries as coded in experiments/e17_close.py -> [(setup, up, e)]."""
    win = np.flatnonzero((hh >= 9.5) & (hh < 11.5))
    if len(win) < 6:
        return []
    orm = hh < 10
    orh = h[orm].max() if orm.any() else np.nan
    orl = l[orm].min() if orm.any() else np.nan
    out = []
    for up, lvl in ((True, pmh), (False, pml)):
        if not np.isfinite(lvl):
            continue
        brk = next((int(j) for j in win if (up and c[j] > lvl) or (not up and c[j] < lvl)), None)
        if brk is None:
            continue
        for r in range(brk + 3, min(brk + 16, len(c))):
            adv = (h[brk + 1:r].max() - lvl) / lvl if up else (lvl - l[brk + 1:r].min()) / lvl
            if r > brk + 1 and adv < 0.0018:
                continue
            if (up and l[r] <= lvl and c[r] > lvl) or (not up and h[r] >= lvl and c[r] < lvl):
                out.append(("level", up, r))
                break
    out += [("ORB", True, int(j)) for j in win if hh[j] >= 10 and c[j] > orh][:1]
    out += [("ORB", False, int(j)) for j in win if hh[j] >= 10 and c[j] < orl][:1]
    out += [("VWAP", True, int(j)) for j in win if j > 2 and c[j - 1] < vwap[j - 1] and c[j] > vwap[j]][:CAP]
    out += [("VWAP", False, int(j)) for j in win if j > 2 and c[j - 1] > vwap[j - 1] and c[j] < vwap[j]][:CAP]
    out += [("pullback", True, int(j)) for j in win if j > 3 and (h[:j].max() / o[0] - 1) > 0.005 and c[j] < o[j]][:CAP]
    out += [("pullback", False, int(j)) for j in win if j > 3 and (1 - l[:j].min() / o[0]) > 0.005 and c[j] > o[j]][:CAP]
    return [(s, up, e) for s, up, e in out if e < len(c) - 8]


def structural_stop(setup, up, e, h, l, c, vwap, orh, orl, pmh, pml, b):
    """The stop at the setup's own structure, pushed out by b (a price distance)."""
    if setup == "ORB":
        return orl - b if up else orh + b
    if setup == "level":
        return min(pmh, l[e]) - b if up else max(pml, h[e]) + b
    if setup == "VWAP":                       # the dip under VWAP that bar e reclaimed
        k = e - 1
        if up:
            while k >= 0 and c[k] < vwap[k]:
                k -= 1
            return l[k + 1:e + 1].min() - b
        while k >= 0 and c[k] > vwap[k]:
            k -= 1
        return h[k + 1:e + 1].max() + b
    if setup == "pullback":                   # the pullback since the session's extreme so far
        if up:
            m = np.flatnonzero(h[:e + 1] == h[:e + 1].max())[-1]
            return (l[m + 1:e + 1].min() if m < e else l[e]) - b
        m = np.flatnonzero(l[:e + 1] == l[:e + 1].min())[-1]
        return (h[m + 1:e + 1].max() if m < e else h[e]) + b
    raise ValueError(setup)


def simulate(O, H, L, c_last, fill, ups, stops, tgts):
    """Bracket trades filled at `fill` (the open of the first bar in O/H/L).

    O, H, L: the bars from entry to the time exit. Stop is checked before target,
    and a bar that opens beyond a barrier fills at its open. Unhit -> c_last.
    Returns (gross R, outcome 0 stop / 1 target / 2 time / 3 stop on a bar that also
    reached the target); NaN R where the risk is
    zero, on the wrong side, or under MIN_RISK of the price.
    """
    ups = np.asarray(ups, bool); stops = np.asarray(stops, float); tgts = np.asarray(tgts, float)
    sgn = np.where(ups, 1.0, -1.0)
    risk = sgn * (fill - stops)
    n = len(O)
    hs = np.where(ups[:, None], L[None, :] <= stops[:, None], H[None, :] >= stops[:, None])
    ht = np.where(ups[:, None], H[None, :] >= tgts[:, None], L[None, :] <= tgts[:, None])
    fs = np.where(hs.any(1), hs.argmax(1), n)
    ft = np.where(ht.any(1), ht.argmax(1), n)
    stop_hit = (fs < n) & (fs <= ft)
    tgt_hit = ~stop_hit & (ft < n)
    # one bar reaches both and opened between them: the order is unknown, stop assumed
    Of = O[np.minimum(fs, n - 1)]
    amb = stop_hit & (fs == ft) & (sgn * (Of - stops) > 0) & (sgn * (tgts - Of) > 0)
    Os = O[np.minimum(fs, n - 1)]; Ot = O[np.minimum(ft, n - 1)]
    px = np.where(stop_hit, np.where(ups, np.minimum(stops, Os), np.maximum(stops, Os)),
         np.where(tgt_hit, np.where(ups, np.maximum(tgts, Ot), np.minimum(tgts, Ot)), c_last))
    with np.errstate(divide="ignore", invalid="ignore"):
        R = sgn * (px - fill) / risk
    ok = np.isfinite(risk) & (risk > 0) & (risk / fill >= MIN_RISK)
    return np.where(ok, R, np.nan), np.where(amb, 3, np.where(stop_hit, 0, np.where(tgt_hit, 1, 2)))


def atr_at(ranges, n_tail, e):
    """Mean range of the ATR_N bars before bar e. `ranges` = prior-session tail + today."""
    k = n_tail + e
    return ranges[k - ATR_N:k].mean() if k >= ATR_N else np.nan


def session_trades(o, h, l, c, v, hh, pre_h, pre_l, tail_ranges, pdh, pdl):
    """Phase 1 for one name-session: every entry, its structural stops, and its path.

    tail_ranges: high - low of the prior session's last RTH bars (for ATR at the open).
    pdh, pdl: the prior session's RTH high and low (for the level-target variant).
    """
    if len(c) < 40 or len(pre_h) < 5:
        return []
    vwap = np.cumsum((h + l + c) / 3 * v) / np.maximum(np.cumsum(v), 1)
    pmh, pml = pre_h.max(), pre_l.min()
    orm = hh < 10
    orh, orl = (h[orm].max(), l[orm].min()) if orm.any() else (np.nan, np.nan)
    tail = np.asarray(tail_ranges, float)[-ATR_N:]
    ranges = np.r_[tail, h - l]
    out = []
    for setup, up, e in signals(o, h, l, c, hh, vwap, pmh, pml):
        a = atr_at(ranges, len(tail), e)
        if not (np.isfinite(a) and a > 0):
            continue
        fill = o[e + 1]
        end = min(len(c), e + 1 + MAXB)
        s = 1.0 if up else -1.0
        stops = {b: structural_stop(setup, up, e, h, l, c, vwap, orh, orl, pmh, pml, b * a) for b in BUFFERS}
        out.append(dict(
            setup=setup, up=up, e=e, t=hh[e], fill=fill, atr=a,
            O=o[e + 1:end], H=h[e + 1:end], L=l[e + 1:end], c_last=c[end - 1],
            stops=stops, widths={b: s * (fill - stops[b]) / a for b in BUFFERS},
            v_stop=fill - s * 2 * (h[e] - l[e]),
            mom=np.sign(c[e] - c[e - MOM_K]) if e >= MOM_K else 0.0,
            orb_mid=(orh + orl) / 2,
            lvl_tgts=(pdh, pmh) if up else (pdl, pml)))
    return out


def _level_target(t, risk):
    """Nearest level in the trade's direction at least 1R from the fill, else 2R."""
    s = 1.0 if t["up"] else -1.0
    lv = [x for x in t["lvl_tgts"] if np.isfinite(x) and s * (x - t["fill"]) >= risk]
    return (min(lv) if t["up"] else max(lv)) if lv else t["fill"] + s * 2 * risk


def score_month(trades, rng):
    """Phase 2 for one calendar month of trades -> one result dict per trade.

    The control for a trade borrows the structural width (in ATR) of another trade
    with the same setup and side in the same month, N_DRAWS times.
    """
    pools = {}
    for i, t in enumerate(trades):
        for b in BUFFERS:
            if t["widths"][b] > 0:
                pools.setdefault((t["setup"], t["up"], b), []).append(i)
    rows = []
    for i, t in enumerate(trades):
        up, fill, a = t["up"], t["fill"], t["atr"]
        s = 1.0 if up else -1.0
        U, S, T, tags = [], [], [], []

        def add(tag, side_up, stop, tgt):
            U.append(side_up); S.append(stop); T.append(tgt); tags.append(tag)

        for b in BUFFERS:
            st = t["stops"][b]; risk = s * (fill - st)
            for k in TARGETS:
                add(("S", b, k), up, st, fill + s * k * risk)
            pool = [j for j in pools.get((t["setup"], up, b), []) if j != i]
            draws = rng.choice(pool, size=N_DRAWS, replace=True) if pool else []
            for d, j in enumerate(draws):
                w = trades[j]["widths"][b] * a
                for k in TARGETS:
                    add(("C", b, k, d), up, fill - s * w, fill + s * k * w)
            if t["mom"] != 0:
                mu = t["mom"] > 0; ms = 1.0 if mu else -1.0
                for k in TARGETS:
                    add(("M", b, k), mu, fill - ms * risk, fill + ms * k * risk)
        vr = s * (fill - t["v_stop"])
        for k in TARGETS:
            add(("V", k), up, t["v_stop"], fill + s * k * vr)
        if t["setup"] == "ORB":
            mr = s * (fill - t["orb_mid"])
            add(("ORBmid",), up, t["orb_mid"], fill + s * PRIMARY_T * mr)
        pst = t["stops"][PRIMARY_B]
        add(("LT",), up, pst, _level_target(t, s * (fill - pst)))

        R, out = simulate(t["O"], t["H"], t["L"], t["c_last"], fill, U, S, T)
        risk = np.where(np.asarray(U), 1.0, -1.0) * (fill - np.asarray(S, float))
        with np.errstate(divide="ignore", invalid="ignore"):
            cost = 1e-4 * fill / risk                        # R per bp of round-trip cost
        row = dict(setup=t["setup"], up=up, t=t["t"], fill=fill, atr=a)
        ctl = {}
        for tag, r, o_, cs in zip(tags, R, out, cost):
            if tag[0] == "C":
                if np.isfinite(r):
                    ctl.setdefault(tag[1:3], []).append((r, cs))
                continue
            key = "_".join(str(x) for x in tag)
            row[f"R_{key}"] = r
            row[f"c_{key}"] = cs if np.isfinite(r) else np.nan
            row[f"o_{key}"] = o_
        for b in BUFFERS:
            row[f"w_{b}"] = t["widths"][b]
            row[f"bp_{b}"] = 1e4 * t["widths"][b] * a / fill
            for k in TARGETS:
                v = np.array(ctl.get((b, k), []))
                row[f"R_C_{b}_{k}"] = v[:, 0].mean() if len(v) else np.nan
                row[f"c_C_{b}_{k}"] = v[:, 1].mean() if len(v) else np.nan
                row[f"n_C_{b}_{k}"] = len(v)
        row["M_same"] = (t["mom"] > 0) == up if t["mom"] != 0 else np.nan
        rows.append(row)
    return rows
