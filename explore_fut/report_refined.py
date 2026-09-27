"""The tests in prereg/fut_zone_refined.md. Standard errors cluster by calendar week
(trades run for days, and four of the five markets are dollar pairs).

  python3 explore_fut/report_refined.py [dev|holdout]
"""
import pandas as pd, numpy as np, sys

def wk_t(x, t):
    """mean, week-clustered se, t"""
    g = pd.Series(np.asarray(x) - np.mean(x)).groupby(pd.to_datetime(t).dt.to_period("W").values).sum()
    se = np.sqrt((g ** 2).sum()) / len(x)
    return np.mean(x), se, np.mean(x) / se if se > 0 else np.nan

def line(name, m, se, t, extra=""):
    print(f"  {name:44s} {m:+.3f}  se {se:.3f}  t {t:+.2f}  {extra}")

period = sys.argv[1] if len(sys.argv) > 1 else "dev"; suf = "" if period == "dev" else "_holdout"
T = pd.read_parquet(f"cache/fut_zone_refined{suf}.parquet").dropna(subset=["R"])
K = pd.read_parquet(f"cache/fut_zone_refined_ctrl{suf}.parquet").dropna(subset=["R"])
print(f"== TEST A: refined-stop zone trade vs random control ({period}) ==")
print(f"  {len(T)} trades; stop floored in {T.floored.mean():.0%}; median stop {T.stop_atr.median():.2f} x ATR5, "
      f"{T.R_ticks.median():.0f} ticks; median planned R:R {T.rr.median():.1f}")
hit, be = (T.how == "target").mean(), (1 / (1 + T.rr)).mean()
line("zone trades, mean R", *wk_t(T.R, T.fill_t), f"hit {hit:.2f} vs break-even {be:.2f}")
line("random control, mean R", K.R.mean(), np.nan, np.nan, f"hit {(K.how=='target').mean():.2f}  ({len(K)} draws)")
cm = K.groupby("of").R.mean(); d = T.R - T.fill_t.map(cm)
ok = d.notna()
m, se, t = wk_t(d[ok], T.fill_t[ok])
line("zone minus its own controls", m, se, t)
print(f"  PASS rule: difference > 0 with t >= {2.0 if period == 'dev' else 1.65}  ->  "
      f"{'PASS' if t >= (2.0 if period == 'dev' else 1.65) else 'FAIL'}")
print(T.groupby("sym").R.agg(["size", "mean"]).round(2).T.to_string())

if period == "holdout":
    Z = pd.read_parquet("cache/fut_zone_trades_holdout.parquet"); Z = Z[Z.filled]
    B = Z[(Z.rr >= 5) & (Z.rr < 8)].copy()
    B["R"] = B.R - (B.how == "stop") / B.R_ticks                     # + 1 tick slippage on stops
    print(f"\n== TEST B: the 5-8 planned R:R bucket of the limit-order version (holdout) ==")
    m, se, t = wk_t(B.R, B.fill_t)
    line(f"{len(B)} trades, mean R", m, se, t, f"hit {(B.how=='target').mean():.2f} vs break-even {(1/(1+B.rr)).mean():.2f}")
    print(f"  PASS rule: mean R > 0 with t >= 1.65  ->  {'PASS' if t >= 1.65 else 'FAIL'}")
