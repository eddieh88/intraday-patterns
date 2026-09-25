"""Prior-day S/R, broken and retested during the opening hours.

Levels intraday traders actually watch, all known BEFORE 9:30:
    PDH / PDL   prior day's regular-session high / low
    PDC         prior day's close
    ONH / ONL   overnight high / low (04:00-09:30)

A break is a 5-minute CLOSE beyond the level.  A retest requires, as the daily
work showed it must, real separation: at least MIN_GAP bars later, and only
after price has ADVANCED at least MIN_ADV beyond the level first.  Without
those, 73% of 'retests' are just the next bar dipping back.

Scaled from the daily version by bar range: daily bars run ~2.18% and used a
2% advance, so at a ~0.20% 5-minute bar the equivalent is ~0.18%.
"""
import pandas as pd, numpy as np, glob

MIN_GAP, MIN_ADV, RWIN = 3, 0.0018, 12      # bars; 12 bars = 1 hour
TRADE_START, TRADE_END = 9.5, 11.5          # only look for setups in the open

def session_frames(files, symbols):
    """yield (symbol, date, DataFrame of that day's 5-min bars incl. pre-market)"""
    for f in files:
        d = pd.read_parquet(f, columns=["timestamp","symbol","open","high","low","close","volume"])
        d["symbol"] = d.symbol.str.replace("-DELISTED","",regex=False)
        d = d[d.symbol.isin(symbols)]
        if not len(d): continue
        t = pd.to_datetime(d.timestamp)
        d = d.assign(ts=t, h=t.dt.hour + t.dt.minute/60).sort_values("ts")
        for s, g in d.groupby("symbol"):
            yield s, t.iloc[0].normalize(), g.reset_index(drop=True)

def find_setups(g, levels):
    """g = one session incl. pre-market.  levels = {name: price}, all known pre-open."""
    rth = g[(g.h >= 9.5) & (g.h < 16)].reset_index(drop=True)
    if len(rth) < 40: return []
    o,h,l,c = (rth[k].values.astype(float) for k in ("open","high","low","close"))
    hh = rth.h.values
    out = []
    for name, R in levels.items():
        if R is None or not np.isfinite(R) or R <= 0: continue
        for b in range(1, len(c)-6):
            if not (TRADE_START <= hh[b] < TRADE_END): continue
            if not (c[b-1] <= R < c[b]): continue                  # upside break
            for r in range(b+MIN_GAP, min(b+1+RWIN, len(c)-3)):
                if h[b+1:r].size and (h[b+1:r].max()-R)/R < MIN_ADV: continue
                if l[r] <= R:                                       # returned to the level
                    kind = "bounce" if c[r] > R else "failure"
                    out.append(dict(level=name, R=R, brk=b, entry=r, kind=kind))
                    break
            break                                                   # first break only
    return out
