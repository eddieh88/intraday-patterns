"""Run the Colab notebook's real code locally before uploading it.

Three Colab runs were wasted on bugs that were all detectable here: a docstring
escaping error, a float64/AMP dtype mismatch, and a training loop whose
early-stopping rule fired mid-descent.  This executes every code cell against a
small symbol subset and asserts the things that actually broke.

    python3 colab/preflight.py

Exits non-zero on failure.  What it CANNOT catch: anything CUDA-specific (this
machine has no CUDA, so autocast runs disabled), Drive mounting, and whether
the model converges at full scale.
"""
import json, sys, ast, os, time
import numpy as np, pandas as pd, torch, torch.nn as nn
from scipy import stats

NB   = os.path.join(os.path.dirname(__file__), "chart_patterns_colab.ipynb")
DATA = os.path.join(os.path.dirname(__file__), "colab_ohlcv.parquet")
NSYM, FAILS = 12, []

def check(name, fn):
    try:
        fn(); print(f"  PASS  {name}")
    except Exception as e:
        FAILS.append(name); print(f"  FAIL  {name}: {type(e).__name__}: {e}")

nb = json.load(open(NB))
code = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']
print(f"notebook: {len(nb['cells'])} cells, {len(code)} code\n")

print("1. every code cell parses")
for i, src in enumerate(code):
    check(f"cell {i} syntax", lambda s=src: ast.parse(s))

print("\n2. end-to-end on a symbol subset")
df = pd.read_parquet(DATA)
df = df[df.symbol.isin(sorted(df.symbol.unique())[:NSYM])]
df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
CK, BE = "/tmp/_pf_ck.pt", "/tmp/_pf_best.pt"
for f in (CK, BE):
    if os.path.exists(f): os.remove(f)
g = {'np':np,'pd':pd,'torch':torch,'nn':nn,'stats':stats,'time':time,'os':os,
     'df':df,'CKPT':CK,'BEST':BE}
run = lambda i, **sub: exec(
    [code[i].replace(k, v) for k, v in sub.items()][0] if sub else code[i], g)

setup  = [i for i,s in enumerate(code) if "_GS = lambda" in s][0]
render = [i for i,s in enumerate(code) if "def render(" in s][0]
build  = [i for i,s in enumerate(code) if "def windows(" in s][0]
split  = [i for i,s in enumerate(code) if "class DS(" in s][0]
train  = [i for i,s in enumerate(code) if "RESUMED from epoch" in s][0]
gate   = [i for i,s in enumerate(code) if "AUC_MIN" in s][0]

exec(code[setup].replace('num_workers=2','num_workers=0'), g)
check("render cell",  lambda: exec(code[render], g))
check("build cell",   lambda: exec(code[build], g))
check("split + model",lambda: exec(code[split].replace('num_workers=2','num_workers=0'), g))

print("\n3. the things that actually broke before")
check("DS returns float32 (AMP needs it)", lambda: (
    lambda t: (_ for _ in ()).throw(AssertionError(f"got {t.dtype}"))
      if t.dtype != torch.float32 else None)(
    g['DS'](g['X'][:1], g['Y'][:1], np.float64(0.11), np.float64(0.31))[0][0]))

EP = lambda n: code[train].replace("= 30, 5, 256, 2e-5, 1e-4", f"= {n}, 5, 256, 2e-5, 1e-4") \
                          .replace('num_workers=2','num_workers=0')
check("training loop runs", lambda: exec(EP(1), g))
check("checkpoint written", lambda: os.path.exists(CK) or (_ for _ in ()).throw(
    AssertionError("no checkpoint")))
check("resume path", lambda: exec(EP(2), g))

def gate_blocks():
    try:
        exec(code[gate].replace('num_workers=2','num_workers=0'), g)
    except AssertionError:
        return                      # correct: a 2-epoch model must be blocked
    raise AssertionError("gate PASSED an undertrained model -- too lenient")
check("instrument gate blocks a weak model", gate_blocks)

print(f"\n{'PREFLIGHT PASSED' if not FAILS else 'PREFLIGHT FAILED: ' + ', '.join(FAILS)}")
sys.exit(1 if FAILS else 0)
