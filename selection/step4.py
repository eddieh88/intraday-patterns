"""Step 4 of prereg/selection.md: the economic gate (Amendment 1 form).

Ranks out-of-sample name-days on a model's predicted continuation and asks
whether the best fifth pays after costs. Two gates, two cost models:

  pooled          top fifth of all out-of-sample name-days
  within-session  top fifth of names inside each session (removes day timing)

  cost (a)  3bp through each trade's own 1R      net_a3
  cost (b)  flat 0.023R                          net_b

A gate PASSES only if, under BOTH costs, the top fifth's mean net R has a
session-clustered confidence interval entirely above zero AND top minus bottom
is positive with clustered t above the same critical value.

  python3 selection/step4.py cache/sel_oos.parquet ridge 1.96
"""
import pandas as pd, numpy as np, sys
import statsmodels.api as sm

def clustered(y, groups, x=None):
    X = np.ones((len(y), 1)) if x is None else sm.add_constant(x)
    m = sm.OLS(np.asarray(y, float), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(groups)[0]})
    return m.params[-1], m.bse[-1], m.tvalues[-1]

def gate(D, qcol, z, costs):
    top, bot = D[D[qcol] == 4], D[D[qcol] == 0]
    both = pd.concat([top.assign(t=1.0), bot.assign(t=0.0)])
    rows, ok = [], True
    for c in costs:
        m, se, _ = clustered(top[c], top.date)
        d, _, t = clustered(both[c], both.date, both.t.values)
        passed = (m - z * se > 0) and (d > 0) and (t > z)
        ok &= passed if c in ("net_a3", "net_b") else True
        rows.append(dict(cost=c, top_mean=m, ci_lo=m - z * se, ci_hi=m + z * se, top_minus_bottom=d, t=t,
                         result=("PASS" if passed else "fail") if c in ("net_a3", "net_b") else "(reported)"))
    return ok, pd.DataFrame(rows)

def main(path, label, z):
    z = float(z)
    P = pd.read_parquet(path); O = pd.read_parquet("cache/sel_outcomes.parquet")
    D = P.merge(O, on=["date","symbol"])
    D["q_pooled"] = pd.qcut(D.pred.rank(method="first"), 5, labels=False)
    D["q_within"] = D.groupby("date").pred.transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False))
    costs = ["net_a3", "net_b", "net_a6", "r_gross"]
    print(f"STEP 4 -- {label}: {len(D):,} out-of-sample name-days, {D.date.nunique()} sessions, "
          f"critical value {z:.2f} ({'95%' if abs(z-1.96)<.01 else f'{(1-2*(1-__import__('scipy').stats.norm.cdf(z)))*100:.1f}%'} two-sided)\n")
    print("net R by quintile of predicted continuation (0 = worst, 4 = best):")
    for qcol, name in (("q_pooled", "pooled"), ("q_within", "within-session")):
        tab = D.groupby(qcol)[costs].mean()
        tab.index = [f"{name} Q{i}" for i in tab.index]
        print(tab.to_string(float_format=lambda v: f"{v:+.4f}"))
    verdicts = {}
    for qcol, name in (("q_pooled", "POOLED"), ("q_within", "WITHIN-SESSION")):
        ok, tab = gate(D, qcol, z, costs)
        verdicts[name] = ok
        print(f"\n{name} gate: {'PASS' if ok else 'FAIL'}")
        print(tab.to_string(index=False, float_format=lambda v: f"{v:+.4f}"))
    top = D[D.q_pooled == 4]; per = top.groupby("date").size().sort_values(ascending=False)
    print(f"\npooled top fifth: {len(top):,} name-days from {per.size} of {D.date.nunique()} sessions; "
          f"the busiest 10% of sessions hold {per.iloc[:max(1, per.size//10)].sum()/len(top):.0%} of it")
    print(f"exits, all trades: {D.exit.value_counts(normalize=True).round(3).to_dict()}")
    reading = {(True, True): "stock selection -> step 5 on stocks",
               (True, False): "index timing -> step 5 on ES/NQ; stock holdout stays sealed",
               (False, True): "relative selection only -> step 5 as a within-day ranking rule",
               (False, False): "nothing -> STOP"}[(verdicts["POOLED"], verdicts["WITHIN-SESSION"])]
    print(f"\nREADING (registered table): {reading}")

if __name__ == "__main__":
    main(*sys.argv[1:])
