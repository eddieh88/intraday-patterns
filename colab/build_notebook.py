import json

MD = lambda s: {"cell_type":"markdown","metadata":{},"source":s.splitlines(keepends=True)}
CO = lambda s: {"cell_type":"code","metadata":{},"execution_count":None,"outputs":[],
                "source":s.splitlines(keepends=True)}
cells = []

cells.append(MD("""# Do textbook chart patterns predict anything?

A pre-registered test of the patterns sold in retail trading education
(head-and-shoulders, double bottom, breakout-retest, ...), using the method from
Jiang, Kelly & Xiu, *(Re-)Imag(in)ing Price Trends*, JF 2023.

**The logic.** Train a CNN on real price charts to predict forward returns. Then
feed it *synthetic* images of each textbook pattern and ask what it predicts.
The CNN is not ground truth, but it is an instrument calibrated on real data,
and it lets us ask whether the named patterns carry the direction folk wisdom
assigns them.

**JKX found on US daily data 1993-2019:** of 23 textbook patterns, 13 had a
significant association with CNN forecasts -- and **8 of those 13 pointed the
opposite way to the folk wisdom.** Their conclusion: some price patterns are
predictive, but the ones in the books are not.

This notebook re-runs that probe on *our own* survivorship-inclusive panel.

## Pre-registration -- fixed before any model is fit

- **Instrument.** CNN on 20-day OHLC+volume images (60x64 binary), trained to
  classify the sign of the forward 5-day return. Train 2010-2017, validate
  2018-2019, test 2020-2026.
- **Primary statistic.** For each textbook pattern, the CNN's mean predicted
  P(up) over 10,000 simulated images, and whether it differs from the Brownian
  control at p < 0.01 (Bonferroni-corrected across patterns).
- **The control that makes this a test.** Images simulated from driftless
  Brownian motion. If the CNN does not return ~50% on those, the instrument is
  broken and every other number here is void. **This is checked first and the
  notebook stops if it fails.**
- **Decision.** A pattern "works as advertised" only if it is significant AND
  signed in the direction the textbooks claim. We report the count of
  significant-and-correct vs significant-and-inverted.
- **What this cannot show.** Daily bars. It says nothing about 5-minute charts,
  and nothing about whether a pattern is *tradeable* after costs.

Prior, recorded now: expect most patterns insignificant, and a meaningful
fraction of the significant ones inverted, as in JKX."""))

cells.append(MD("## 1. Setup"))
cells.append(CO("""import torch, torch.nn as nn, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
dev = "cuda" if torch.cuda.is_available() else "cpu"
print("torch", torch.__version__, "| device:", dev)
if dev == "cpu":
    print("WARNING: no GPU. Runtime > Change runtime type > T4 GPU.")"""))

cells.append(MD("""## 2. Data

Upload `colab_ohlcv.parquet` (built locally). Universe is the top 500 names by
dollar volume **as of 2010, then frozen** -- names that later delisted are kept,
so the panel is not survivorship-filtered."""))
cells.append(CO("""from google.colab import files
up = files.upload()            # choose colab_ohlcv.parquet
df = pd.read_parquet(next(iter(up)))
df["timestamp"] = pd.to_datetime(df.timestamp)
print(f"{len(df):,} rows | {df.symbol.nunique()} names | "
      f"{df.timestamp.min().date()} .. {df.timestamp.max().date()}")
last = df.groupby("symbol").timestamp.max()
print(f"names ending >30d early (delisted, retained): "
      f"{(last < df.timestamp.max() - pd.Timedelta(days=30)).sum()}")
print(f"days flagged corrupt (skipped): {df.bad_day.sum()}")

# validation gate -- these must all be zero or the panel is not usable
assert (df[["open","high","low","close"]] > 0).all().all(), "non-positive price"
assert (df.high >= df.low).all(), "high < low"
print("validation gate: PASSED")"""))

cells.append(MD("""## 3. Image construction

JKX's format: each day occupies 3 pixels of width (open mark, high-low bar,
close mark). Prices are converted to cumulative returns so the image is
invariant to price level and to splits, then scaled so the path fills the
frame. Volume bars occupy the bottom fifth. Black background, white marks,
binary -- no RGB channel needed."""))
cells.append(CO("""H, W_PER_DAY, NDAYS = 64, 3, 20
W = W_PER_DAY * NDAYS
VOL_H = H // 5                      # volume panel height
PRICE_H = H - VOL_H

def make_image(o, h, l, c, v):
    \"\"\"OHLCV arrays of length NDAYS -> (H, W) uint8 image, or None if degenerate.\"\"\"
    c0 = c[0]
    if not np.isfinite(c0) or c0 <= 0: return None
    o, h, l, c = (x / c0 for x in (o, h, l, c))      # level-invariant
    lo, hi = np.nanmin(l), np.nanmax(h)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo: return None
    img = np.zeros((H, W), dtype=np.uint8)
    y = lambda p: int(np.clip(round((p - lo) / (hi - lo) * (PRICE_H - 1)), 0, PRICE_H - 1))
    for d in range(NDAYS):
        if not np.isfinite([o[d], h[d], l[d], c[d]]).all(): continue
        x = d * W_PER_DAY
        img[PRICE_H - 1 - y(h[d]) : PRICE_H - y(l[d]), x + 1] = 255   # high-low bar
        img[PRICE_H - 1 - y(o[d]), x] = 255                            # open tick
        img[PRICE_H - 1 - y(c[d]), x + 2] = 255                        # close tick
    vmax = np.nanmax(v) if np.isfinite(v).any() else 0
    if vmax > 0:
        for d in range(NDAYS):
            if not np.isfinite(v[d]): continue
            vh = int(round(v[d] / vmax * (VOL_H - 1)))
            if vh > 0: img[H - vh:, d * W_PER_DAY + 1] = 255
    return img

print(f"image: {H} x {W} binary = {H*W:,} px, {H*W/8/1024:.2f} KB bit-packed")"""))

cells.append(MD("## 4. Build the training set"))
cells.append(CO("""FWD = 5     # forward horizon, days

def build(sym_df):
    o,h,l,c,v = (sym_df[k].values.astype(np.float64)
                 for k in ("open","high","low","close","volume"))
    t = sym_df.timestamp.values
    bad = sym_df.bad_day.values          # days adjacent to an unadjusted split
    X, Y, T = [], [], []
    for i in range(NDAYS, len(c) - FWD):
        # skip any window or forward period containing a known-corrupt day.
        # the vendor does not reliably adjust reverse splits, and one bad day
        # inside the window corrupts the whole image, not just the label.
        if bad[i-NDAYS : i+FWD].any(): continue
        img = make_image(o[i-NDAYS:i], h[i-NDAYS:i], l[i-NDAYS:i],
                         c[i-NDAYS:i], v[i-NDAYS:i])
        if img is None: continue
        r = c[i+FWD-1]/c[i-1] - 1.0
        if not np.isfinite(r) or abs(r) > 3.0: continue
        X.append(np.packbits(img > 0)); Y.append(1 if r > 0 else 0); T.append(t[i])
    return X, Y, T

Xs, Ys, Ts = [], [], []
for j,(s, g) in enumerate(df.groupby("symbol", sort=False)):
    a,b,t = build(g.sort_values("timestamp"))
    Xs += a; Ys += b; Ts += t
    if j % 100 == 0: print(f"  {j} names, {len(Xs):,} images", flush=True)

X = np.stack(Xs); Y = np.array(Ys, dtype=np.int64); T = pd.to_datetime(np.array(Ts))
print(f"\\n{len(X):,} images | packed {X.nbytes/1e6:.0f} MB "
      f"(unpacked would be {len(X)*H*W/1e9:.1f} GB)")
print(f"base rate P(up) = {Y.mean():.4f}")"""))

cells.append(MD("""## 5. Split and train

Chronological split -- no shuffling across time."""))
cells.append(CO("""tr = T < "2018-01-01"
va = (T >= "2018-01-01") & (T < "2020-01-01")
te = T >= "2020-01-01"
print(f"train {tr.sum():,} | val {va.sum():,} | test {te.sum():,}")

class DS(torch.utils.data.Dataset):
    def __init__(s, X, Y): s.X, s.Y = X, Y
    def __len__(s): return len(s.X)
    def __getitem__(s, i):
        img = np.unpackbits(s.X[i])[:H*W].reshape(1, H, W).astype(np.float32)
        return torch.from_numpy(img), s.Y[i]

class CNN(nn.Module):
    \"\"\"JKX-style: 3 blocks of (conv 5x3, BN, LeakyReLU, maxpool), then linear.\"\"\"
    def __init__(s):
        super().__init__()
        def blk(i, o): return nn.Sequential(
            nn.Conv2d(i, o, (5,3), padding=(2,1)), nn.BatchNorm2d(o),
            nn.LeakyReLU(0.01), nn.MaxPool2d((2,1)))
        s.f = nn.Sequential(blk(1,64), blk(64,128), blk(128,256), nn.Flatten(),
                            nn.Dropout(0.5))
        s.head = nn.Linear(256 * (H//8) * W, 2)
    def forward(s, x): return s.head(s.f(x))

torch.manual_seed(0)
m = CNN().to(dev)
print(f"{sum(p.numel() for p in m.parameters()):,} parameters")"""))

cells.append(CO("""opt = torch.optim.Adam(m.parameters(), lr=1e-5)
lossf = nn.CrossEntropyLoss()
dl_tr = torch.utils.data.DataLoader(DS(X[tr], Y[tr]), batch_size=128, shuffle=True,
                                    num_workers=2, drop_last=True)
dl_va = torch.utils.data.DataLoader(DS(X[va], Y[va]), batch_size=512, num_workers=2)

best, bad, EPOCHS, PATIENCE = 1e9, 0, 20, 3
for ep in range(EPOCHS):
    m.train()
    for xb, yb in dl_tr:
        xb, yb = xb.to(dev), yb.to(dev)
        opt.zero_grad(); loss = lossf(m(xb), yb); loss.backward(); opt.step()
    m.eval(); vl = n = 0
    with torch.no_grad():
        for xb, yb in dl_va:
            xb, yb = xb.to(dev), yb.to(dev)
            vl += lossf(m(xb), yb).item() * len(yb); n += len(yb)
    vl /= n
    print(f"epoch {ep+1:2d}  val loss {vl:.5f}" + ("  *" if vl < best else ""), flush=True)
    if vl < best:
        best, bad = vl, 0
        torch.save(m.state_dict(), "best.pt")
    else:
        bad += 1
        if bad >= PATIENCE: print("early stop"); break
m.load_state_dict(torch.load("best.pt")); m.eval()"""))

cells.append(MD("""## 6. Does the instrument work? (test-set check)

Before probing patterns, confirm the CNN learned something real out of sample."""))
cells.append(CO("""def predict(Xarr, bs=512):
    out = []
    dl = torch.utils.data.DataLoader(DS(Xarr, np.zeros(len(Xarr), dtype=np.int64)),
                                     batch_size=bs, num_workers=2)
    with torch.no_grad():
        for xb, _ in dl:
            out.append(torch.softmax(m(xb.to(dev)), 1)[:, 1].cpu().numpy())
    return np.concatenate(out)

p_te = predict(X[te]); y_te = Y[te]
auc = (stats.rankdata(p_te)[y_te == 1].mean() - (y_te == 1).sum()/2 - 0.5) / (y_te == 0).sum()
print(f"test accuracy {( (p_te > 0.5) == (y_te == 1) ).mean():.4f}  (base {max(y_te.mean(), 1-y_te.mean()):.4f})")
print(f"test AUC      {auc:.4f}")
print(f"corr(pred, outcome) = {np.corrcoef(p_te, y_te)[0,1]:+.4f}")"""))

cells.append(MD("""## 7. THE CONTROL — Brownian motion must return ~50%

JKX's placebo. Feed the CNN images simulated from driftless random walks. If it
does not return ~0.50, it has learned a bias rather than a pattern, and nothing
below is interpretable. **The notebook stops here if this fails.**"""))
cells.append(CO("""# Simulated images must match the REAL volume distribution.  Flat volume is a
# giveaway the CNN can key on, which would score every synthetic image
# out-of-distribution.  Sample real 20-day volume profiles from the panel.
_vol_pool = []
for _s, _g in df.groupby("symbol", sort=False):
    _v = _g.volume.values.astype(np.float64)
    for _i in range(NDAYS, len(_v), 97):            # thin stride, plenty of draws
        _w = _v[_i-NDAYS:_i]
        if np.isfinite(_w).all() and _w.max() > 0: _vol_pool.append(_w / _w.max())
_vol_pool = np.array(_vol_pool)
print(f"real volume profiles available for simulation: {len(_vol_pool):,}")

def sim_to_image(path, rng):
    \"\"\"close-price path of length NDAYS -> OHLCV image, with REAL volume\"\"\"
    c = path
    o = np.concatenate([[c[0]], c[:-1]])
    spread = np.abs(c - o) * 0.5 + np.abs(c).mean() * 0.004
    h = np.maximum(o, c) + spread * rng.random(NDAYS)
    l = np.minimum(o, c) - spread * rng.random(NDAYS)
    v = _vol_pool[rng.integers(len(_vol_pool))]
    return make_image(o, h, l, c, v)

def probe(path_fn, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    imgs = []
    for k in range(n):
        p = path_fn(rng)
        img = sim_to_image(p, rng)
        if img is not None: imgs.append(np.packbits(img > 0))
    return predict(np.stack(imgs))

SIGMA = 0.02
brown = probe(lambda r: np.cumprod(1 + r.normal(0, SIGMA, NDAYS)))
t, pv = stats.ttest_1samp(brown, 0.5)
print(f"Brownian control: mean P(up) = {brown.mean():.4f}  (sd {brown.std():.4f})")
print(f"  vs 0.50 -> t = {t:+.2f}, p = {pv:.3g}")
OK = abs(brown.mean() - 0.5) < 0.03
print("\\nPLACEBO", "PASSED - instrument usable" if OK else
      "FAILED - the CNN is biased; results below are NOT interpretable")
assert OK, "placebo failed - do not interpret what follows"\n"""))

cells.append(MD("""## 8. The 23 textbook patterns

Each is a stylised price path with the direction folk wisdom assigns it.
`+1` = books say bullish, `-1` = books say bearish."""))
cells.append(CO("""def seg(pts, n):
    \"\"\"piecewise-linear path through control points, length n\"\"\"
    xs = np.linspace(0, len(pts)-1, n)
    return np.interp(xs, np.arange(len(pts)), pts)

# (name, control points, folk-wisdom direction)
PATTERNS = [
 ("Head and shoulders",        [0,.5,.2,1.0,.2,.5,-.1], -1),
 ("Inverse head and shoulders",[0,-.5,-.2,-1.,-.2,-.5,.1], +1),
 ("Double top",                [0,.8,.3,.8,0,-.3],       -1),
 ("Double bottom",             [0,-.8,-.3,-.8,0,.3],     +1),
 ("Triple top",                [0,.8,.3,.8,.3,.8,0],     -1),
 ("Triple bottom",             [0,-.8,-.3,-.8,-.3,-.8,0],+1),
 ("Ascending triangle",        [0,.6,.25,.6,.42,.6,.65], +1),
 ("Descending triangle",       [0,-.6,-.25,-.6,-.42,-.6,-.65], -1),
 ("Symmetric triangle (up)",   [0,.7,-.5,.45,-.25,.2,.5],+1),
 ("Rising wedge",              [0,.5,.25,.7,.5,.85,.75], -1),
 ("Falling wedge",             [0,-.5,-.25,-.7,-.5,-.85,-.75], +1),
 ("Bull flag",                 [0,.9,.75,.85,.7,.8,1.1], +1),
 ("Bear flag",                 [0,-.9,-.75,-.85,-.7,-.8,-1.1], -1),
 ("Pennant (bull)",            [0,1.,.4,.8,.5,.7,1.1],   +1),
 ("Cup and handle",            [0,-.6,-.8,-.6,0,-.2,.3], +1),
 ("Rounding bottom",           [0,-.5,-.8,-.8,-.5,0,.4], +1),
 ("Rounding top",              [0,.5,.8,.8,.5,0,-.4],    -1),
 ("Breakout above resistance", [0,.5,.1,.5,.1,.5,1.0],   +1),
 ("Breakdown below support",   [0,-.5,-.1,-.5,-.1,-.5,-1.], -1),
 ("Breakout then retest",      [0,.2,.6,.35,.42,.6,.9],  +1),
 ("Gap up continuation",       [0,.1,.7,.75,.8,.85,1.0], +1),
 ("Island reversal (top)",     [0,.4,.8,1.0,.5,.1,-.2],  -1),
 ("V-bottom reversal",         [0,-.4,-.9,-.5,0,.4,.7],  +1),
]
print(f"{len(PATTERNS)} patterns")

fig, ax = plt.subplots(4, 6, figsize=(15, 8))
for a,(nm, pts, d) in zip(ax.ravel(), PATTERNS):
    a.plot(seg(pts, 60), color="green" if d>0 else "red", lw=1.5)
    a.set_title(nm, fontsize=7); a.set_xticks([]); a.set_yticks([])
for a in ax.ravel()[len(PATTERNS):]: a.axis("off")
plt.tight_layout(); plt.show()"""))

cells.append(MD("""## 9. Run the probe

Each pattern is rendered 10,000 times with fresh noise and jitter, so the result
reflects the *shape*, not one particular rendering."""))
cells.append(CO("""NOISE = 0.35        # fraction of move size added as iid noise
AMP   = 0.10        # pattern amplitude as a fraction of price

def make_path_fn(pts):
    def f(rng):
        base = seg(pts, NDAYS) * AMP * rng.uniform(0.7, 1.3)
        base = base + rng.normal(0, SIGMA*NOISE, NDAYS).cumsum()
        return np.cumprod(1 + np.diff(np.concatenate([[0], base])))
    return f

rows = []
for i,(nm, pts, d) in enumerate(PATTERNS):
    p = probe(make_path_fn(pts), n=10000, seed=100+i)
    t, pv = stats.ttest_ind(p, brown, equal_var=False)
    rows.append(dict(pattern=nm, folk=d, mean_p_up=p.mean(),
                     vs_brownian=p.mean()-brown.mean(), t=t, p=pv))
    print(f"  {nm:30s} P(up)={p.mean():.4f}  t={t:+7.2f}", flush=True)

R = pd.DataFrame(rows)
ALPHA = 0.01 / len(PATTERNS)                 # Bonferroni
R["significant"] = R.p < ALPHA
R["cnn_dir"] = np.sign(R.vs_brownian)
R["agrees_with_books"] = R.significant & (R.cnn_dir == R.folk)
R["INVERTED"] = R.significant & (R.cnn_dir == -R.folk)
R.sort_values("vs_brownian", ascending=False)"""))

cells.append(MD("## 10. Verdict"))
cells.append(CO("""n_sig = int(R.significant.sum()); n_ok = int(R.agrees_with_books.sum())
n_inv = int(R.INVERTED.sum())
print(f"Bonferroni alpha = {ALPHA:.5f}  ({len(PATTERNS)} patterns)\\n")
print(f"  significant            : {n_sig} of {len(PATTERNS)}")
print(f"  ... as the books claim  : {n_ok}")
print(f"  ... INVERTED            : {n_inv}")
print(f"  not distinguishable     : {len(PATTERNS)-n_sig}")
print(f"\\nJKX on US daily 1993-2019: 13 of 23 significant, 8 of those inverted.")
if n_sig:
    print(f"\\nour inverted share: {n_inv/n_sig:.0%}   (JKX: {8/13:.0%})")

fig, a = plt.subplots(figsize=(9, 7))
s = R.sort_values("vs_brownian")
col = ["#c0392b" if i else ("#27ae60" if o else "#bdc3c7")
       for i,o in zip(s.INVERTED, s.agrees_with_books)]
a.barh(s.pattern, s.vs_brownian, color=col)
a.axvline(0, color="k", lw=.8)
a.set_xlabel("CNN P(up) minus Brownian control")
a.set_title("green = matches the books   red = inverted   grey = not significant")
plt.tight_layout(); plt.show()"""))

cells.append(MD("""## What this does and does not establish

**Does.** Whether a CNN trained on our own survivorship-inclusive panel assigns
the textbook patterns the direction the textbooks claim, with a Brownian placebo
proving the instrument isn't simply biased, and Bonferroni control over 23
simultaneous tests.

**Does not.** (1) Daily bars -- silent on 5-minute charts, which need minute
data we have not pulled. (2) Says nothing about *tradeability*: a significant
directional association is not a strategy, and every strategy in this project so
far has died at the cost step, not the signal step. (3) The CNN is an
instrument, not ground truth -- a pattern it cannot see might still matter.

**If the placebo fails, nothing above is interpretable.** That is the point of
running it first."""))

nb = {"cells": cells, "metadata": {
        "kernelspec": {"display_name":"Python 3","language":"python","name":"python3"},
        "language_info": {"name":"python"},
        "accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"}},
      "nbformat": 4, "nbformat_minor": 0}

p = "exploration/colab/chart_patterns_colab.ipynb"
json.dump(nb, open(p, "w"), indent=1)
print(f"wrote {p}: {len(cells)} cells")
