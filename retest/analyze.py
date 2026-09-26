"""The registered statistics for prereg/retest.md, in its order. Primary first.

  python3 retest/analyze.py
"""
import pandas as pd, numpy as np
import statsmodels.formula.api as smf

R = pd.read_parquet("cache/retest_rows.parquet")
R["real"] = (R.kind == "real").astype(float)
R["retest"] = (R.stage == "retest").astype(float)
R["held"] = (R.a12 > 0).astype(float)

def reg(formula, df, term):
    m = smf.ols(formula, df).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df.date)[0]})
    return m.params[term], m.bse[term], m.tvalues[term]

def mean_se(v, dates):
    m = smf.ols("v ~ 1", pd.DataFrame({"v": v, "d": dates})).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(dates)[0]})
    return m.params.iloc[0], m.bse.iloc[0]

print("DETECTION FUNNEL (touches scored, by kind and stage)")
print(R.groupby(["kind","stage"]).size().unstack().to_string())
print(f"sessions: {R.date.nunique()}   name-days with any scored touch: {R.groupby(['date','symbol']).ngroups:,}")

T = R[R.stage == "retest"]
print("\nPRIMARY -- retests, a12 (from the touching bar's close, 60 min, ATR units, + = level held)")
for k in ("real", "fake"):
    x = T[T.kind == k]; m, se = mean_se(x.a12.values, x.date.values)
    print(f"  {k}: n {len(x):,}   mean {m:+.4f}   SE {se:.4f}   t {m/se:+.2f}")
d, se, t = reg("a12 ~ real", T, "real")
verdict = "SUPPORTED" if (d > 0 and t > 1.96) else "NOT SUPPORTED"
print(f"  real - fake: {d:+.4f}   SE {se:.4f}   t {t:+.2f}   ->  {verdict}")

print("\nSECONDARY (no verdict)")
for lab, f in (("a6, 30 min", "a6 ~ real"), ("share held (a12 > 0)", "held ~ real"),
               ("b12 from the level price -- biased, see Amendment 1", "b12 ~ real")):
    d, se, t = reg(f, T, "real"); print(f"  {lab:52s} real - fake {d:+.4f}  t {t:+.2f}")
print(f"  share held: real {T[T.kind=='real'].held.mean():.3f}   fake {T[T.kind=='fake'].held.mean():.3f}")

print("\n  by level type, real - fake on a12 (Bonferroni over 6: |t| > 2.64)")
for lvl in ["PDH","PDL","P2H","P2L","PMH","PML"]:
    x = T[T.level == lvl]
    if x.kind.nunique() < 2: continue
    d, se, t = reg("a12 ~ real", x, "real")
    print(f"    {lvl}: n real {int(x.real.sum()):6,}  fake {int((1-x.real).sum()):6,}   {d:+.4f}   t {t:+.2f}")

print("\n  approach side, real - fake on a12")
for lab, flag in (("falling into it (support)", True), ("rising into it (resistance)", False)):
    x = T[T.from_above == flag]; d, se, t = reg("a12 ~ real", x, "real")
    print(f"    {lab:30s} {d:+.4f}   t {t:+.2f}")

d, se, t = reg("a12 ~ real * retest", R, "real:retest")
print(f"\n  does testing strengthen a level? (real retest - fake retest) - (real first - fake first)")
F = R[R.stage == "first"]; df_, _, tf = reg("a12 ~ real", F, "real")
print(f"    first touch, real - fake: {df_:+.4f}  t {tf:+.2f}")
print(f"    difference in differences: {d:+.4f}  t {t:+.2f}")
