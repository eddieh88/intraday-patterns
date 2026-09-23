import json
MD = lambda s: {"cell_type":"markdown","metadata":{},"source":s.splitlines(keepends=True)}
CO = lambda s: {"cell_type":"code","metadata":{},"execution_count":None,"outputs":[],
                "source":s.splitlines(keepends=True)}
C=[]

C.append(MD("""# Do textbook chart patterns predict anything?

Pre-registered test of the patterns sold in retail trading education
(head-and-shoulders, double bottom, breakout-and-retest), using the probe from
Jiang, Kelly & Xiu, *(Re-)Imag(in)ing Price Trends*, JF 2023.

**Method.** Train a CNN on real price-chart images to classify the sign of the
forward 5-day return. Then feed it *synthetic* images of each textbook pattern
and ask which direction it predicts. The CNN is not ground truth, but it is an
instrument calibrated on real data.

**JKX found**, on US daily data 1993-2019: of 23 textbook patterns, 13 had a
significant association with CNN forecasts, and **8 of those 13 pointed the
opposite way to the folk wisdom.**

## Pre-registration — fixed before any model is fit

- **Instrument.** CNN on 20-day OHLC + volume + 20-day-MA images (64x60 binary),
  3 conv blocks of 64/128/256 filters — JKX's own I20 architecture.
- **Split, mirroring JKX.** They train and validate on 8 early years with a 70/30
  *random* split (for label balance) and test on the following 19. Here:
  train/val 2010-2015, test 2016-2026.
- **Primary statistic.** For each pattern, mean CNN P(up) over 10,000 simulated
  images, versus the Brownian control, at p < 0.01 Bonferroni-corrected.
- **The control that makes this a test.** Driftless Brownian motion must return
  ~50%. If it does not, the instrument is broken and nothing else here means
  anything. Checked first; the notebook halts on failure.
- **Decision.** A pattern "works as advertised" only if significant AND signed
  the way the books claim. Report significant-and-correct vs -and-inverted.
- **Cannot show.** Daily bars — silent on 5-minute charts. And a directional
  association is not a tradeable strategy.

Prior: most patterns insignificant, a meaningful share of the rest inverted.

**Runtime ~25 min on a T4**: build ~1 min, train ~19 min, probe ~1 min."""))

C.append(MD("## 1. Setup"))
C.append(CO("""import torch, torch.nn as nn, numpy as np, pandas as pd, time, os
import matplotlib.pyplot as plt
from scipy import stats
dev = "cuda" if torch.cuda.is_available() else "cpu"
print("torch", torch.__version__, "| device:", dev)
if dev == "cpu": print("WARNING: no GPU. Runtime > Change runtime type > T4 GPU.")"""))

C.append(MD("""## 2. Data

Upload `colab_ohlcv.parquet`. Universe is the top 500 by dollar volume **as of
2010, then frozen** — names that later delisted are kept, so it is not
survivorship-filtered. A validation gate found real vendor corruption during
construction (sub-penny prices rounding to zero, unadjusted reverse splits,
ticker reuse); `bad_day` flags the residual cases."""))
C.append(CO("""from google.colab import files
up = files.upload()
df = pd.read_parquet(next(iter(up)))
df["timestamp"] = pd.to_datetime(df.timestamp)
df = df.sort_values(["symbol","timestamp"]).reset_index(drop=True)
print(f"{len(df):,} rows | {df.symbol.nunique()} names | "
      f"{df.timestamp.min().date()} .. {df.timestamp.max().date()}")
last = df.groupby("symbol").timestamp.max()
print(f"delisted names retained: {(last < df.timestamp.max()-pd.Timedelta(days=30)).sum()}")
print(f"days flagged corrupt: {df.bad_day.sum()}")
assert (df[["open","high","low","close"]] > 0).all().all(), "non-positive price"
assert (df.high >= df.low).all(), "high < low"
print("validation gate: PASSED")"""))

C.append(MD("""## 3. Image construction — vectorised

JKX's format: each day is 3 px wide (open tick | high-low bar | close tick),
scaled so the path fills the frame, with a 20-day moving-average line drawn
through the middle column and volume in the bottom fifth. Binary, no RGB.

Building these one at a time in Python costs 1,292 us each — 36 minutes for the
full panel. The work is trivially parallel across windows: for each of the 20
day-columns, every window is filled with one broadcast comparison. That is
**22.5 us each, a 57x speedup, verified bit-identical** to the loop version."""))
C.append(CO("""H, WPD, NDAYS, MA_WIN, FWD = 64, 3, 20, 20, 5
W = WPD*NDAYS; VOL_H = H//5; PRICE_H = H-VOL_H
ROWS  = np.arange(PRICE_H)[None,:]
VROWS = np.arange(VOL_H)[None,:]

def render(O, Hh, L, C_, V, M):
    '''(n, NDAYS) arrays -> (n, H, W) uint8 images + a validity mask.
    Shared by real windows and simulated patterns, so both are rendered by
    EXACTLY the same code -- any format difference would let the CNN tell
    them apart and score every pattern out of distribution.'''
    base = C_[:, :1]
    ok = np.isfinite(base[:,0]) & (base[:,0] > 0)
    b = np.where(base > 0, base, 1.0)
    O, Hh, L, C_, M = (x/b for x in (O, Hh, L, C_, M))
    lo = np.nanmin(np.concatenate([L, M], 1), 1)
    hi = np.nanmax(np.concatenate([Hh, M], 1), 1)
    ok &= np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
    rng_ = np.where(hi > lo, hi-lo, 1.0)
    ypix = lambda x: np.clip(np.rint((x-lo[:,None])/rng_[:,None]*(PRICE_H-1)),
                             0, PRICE_H-1).astype(np.int16)
    yO, yH, yL, yC, yM = ypix(O), ypix(Hh), ypix(L), ypix(C_), ypix(M)
    n = len(C_); img = np.zeros((n, H, W), np.uint8)
    for d in range(NDAYS):
        x = d*WPD
        good = np.isfinite(Hh[:,d]) & np.isfinite(L[:,d])     # JKX fn.5
        bar = (ROWS >= (PRICE_H-1-yH[:,d])[:,None]) & (ROWS <= (PRICE_H-1-yL[:,d])[:,None])
        img[:, :PRICE_H, x+1] |= ((bar & good[:,None])*255).astype(np.uint8)
        g = good & np.isfinite(O[:,d]); img[g, PRICE_H-1-yO[g,d], x]   = 255
        g = good & np.isfinite(C_[:,d]); img[g, PRICE_H-1-yC[g,d], x+2] = 255
    mx = np.arange(NDAYS)*WPD + 1                              # MA line
    for xx in range(mx[0], mx[-1]+1):
        j = min(int(np.searchsorted(mx, xx, "right"))-1, NDAYS-2)
        t = (xx-mx[j])/WPD
        yy = np.rint((PRICE_H-1-yM[:,j])*(1-t) + (PRICE_H-1-yM[:,j+1])*t).astype(int)
        g = np.isfinite(M[:,j]) & np.isfinite(M[:,j+1])
        img[g, np.clip(yy[g], 0, PRICE_H-1), xx] = 255
    vmax = np.nanmax(V, 1)
    VN = np.where((np.isfinite(vmax) & (vmax > 0))[:,None],
                  V/np.where(vmax > 0, vmax, 1)[:,None], 0)
    vh = np.rint(np.nan_to_num(VN)*(VOL_H-1)).astype(int)
    for d in range(NDAYS):
        m = (VROWS >= (VOL_H-vh[:,d])[:,None]) & (vh[:,d] > 0)[:,None]
        img[:, PRICE_H:, d*WPD+1] |= (m*255).astype(np.uint8)
    return img, ok

print(f"image {H} x {W} binary = {H*W:,} px, {H*W/8:.0f} B bit-packed")"""))

C.append(MD("""## 4. Build the panel of images

**Stride.** Consecutive 20-day windows share 19 of 20 days — neighbouring images
are ~95% redundant. Striding the train/val set by 3 removes most of that
duplication at negligible information cost, and cuts training time threefold.
The test set is strided by 5 for the same reason."""))
C.append(CO("""SPLIT      = "2016-01-01"     # JKX mirror: early years train/val, rest test
STRIDE_TRV = 3
STRIDE_TE  = 5

def windows(g, stride):
    o,h,l,c,v = (g[k].values.astype(np.float64)
                 for k in ("open","high","low","close","volume"))
    bad = g.bad_day.values
    ma  = pd.Series(c).rolling(MA_WIN).mean().values
    t   = g.timestamp.values
    idx = np.arange(NDAYS+MA_WIN, len(c)-FWD, stride)
    if len(idx) == 0: return None
    win = idx[:,None] - NDAYS + np.arange(NDAYS)[None,:]
    keep = ~np.array([bad[i-NDAYS:i+FWD].any() for i in idx])   # corrupt-day guard
    idx, win = idx[keep], win[keep]
    if len(idx) == 0: return None
    img, ok = render(o[win], h[win], l[win], c[win], v[win], ma[win])
    r = c[idx+FWD-1]/c[idx-1] - 1.0
    ok &= np.isfinite(r) & (np.abs(r) <= 3.0)
    return (np.packbits(img[ok].reshape(ok.sum(), -1) > 0, axis=1),
            (r[ok] > 0).astype(np.int64), t[idx[ok]])

t0 = time.time(); Xs, Ys, Ts = [], [], []
for j,(s,g) in enumerate(df.groupby("symbol", sort=False)):
    for stride, lo, hi in ((STRIDE_TRV, None, SPLIT), (STRIDE_TE, SPLIT, None)):
        sub = g if lo is None else g[g.timestamp >= lo]
        sub = sub if hi is None else sub[sub.timestamp < hi]
        if len(sub) < NDAYS+MA_WIN+FWD+1: continue
        out = windows(sub, stride)
        if out: Xs.append(out[0]); Ys.append(out[1]); Ts.append(out[2])
    if j % 150 == 0: print(f"  {j} names, {sum(len(x) for x in Xs):,} images", flush=True)

X = np.concatenate(Xs); Y = np.concatenate(Ys); T = pd.to_datetime(np.concatenate(Ts))
o = np.argsort(T.values); X, Y, T = X[o], Y[o], T[o]
print(f"\\n{len(X):,} images in {time.time()-t0:.0f}s | packed {X.nbytes/1e6:.0f} MB "
      f"(unpacked would be {len(X)*H*W/1e9:.1f} GB)")
print(f"base rate P(up) = {Y.mean():.4f}")"""))

C.append(MD("## 4b. Cache — so a disconnect does not cost the rebuild"))
C.append(CO("""USE_DRIVE = False
if USE_DRIVE:
    from google.colab import drive; drive.mount("/content/drive")
    CACHE = "/content/drive/MyDrive/chart_patterns_images.npz"
else:
    CACHE = "/content/chart_patterns_images.npz"
np.savez(CACHE, X=X, Y=Y, T=T.values.astype("datetime64[ns]").astype(np.int64))
print(f"cached -> {CACHE} ({os.path.getsize(CACHE)/1e6:.0f} MB)")

# On a later run, execute THIS instead of the build cell:
#   _z = np.load(CACHE); X, Y, T = _z["X"], _z["Y"], pd.to_datetime(_z["T"])"""))

C.append(MD("""## 5. Split and model

JKX split train/validation **randomly** within the early period, explicitly to
balance up/down labels — extended bull or bear stretches would otherwise skew a
chronological validation slice. The test period remains strictly later, so the
out-of-sample claim is unaffected."""))
C.append(CO("""trv = np.asarray(T < SPLIT); te = ~trv
rng = np.random.default_rng(0)
i_trv = np.where(trv)[0]; rng.shuffle(i_trv)
cut = int(0.7*len(i_trv))
i_tr, i_va = i_trv[:cut], i_trv[cut:]
i_te = np.where(te)[0]
print(f"train {len(i_tr):,} | val {len(i_va):,} | test {len(i_te):,}")
print(f"P(up): train {Y[i_tr].mean():.4f}  val {Y[i_va].mean():.4f}  test {Y[i_te].mean():.4f}")

class DS(torch.utils.data.Dataset):
    def __init__(s, X, Y, mu=0.0, sd=1.0): s.X, s.Y, s.mu, s.sd = X, Y, mu, sd
    def __len__(s): return len(s.X)
    def __getitem__(s, i):
        img = np.unpackbits(s.X[i])[:H*W].reshape(1, H, W).astype(np.float32)
        return torch.from_numpy((img-s.mu)/s.sd), s.Y[i]

MU = np.unpackbits(X[i_tr[:20000]], axis=1)[:, :H*W].mean()*1.0   # JKX normalise
SD = max(float(np.sqrt(MU*(1-MU))), 1e-6)
print(f"train pixel mean {MU:.4f}, sd {SD:.4f}")

class CNN(nn.Module):
    '''JKX I20: 3 building blocks, 64/128/256 filters, 5x3 conv, 2x1 max-pool,
    leaky ReLU, batch norm, 50% dropout on the fully connected layer.'''
    def __init__(s):
        super().__init__()
        def blk(i,o): return nn.Sequential(
            nn.Conv2d(i,o,(5,3),padding=(2,1)), nn.BatchNorm2d(o),
            nn.LeakyReLU(0.01), nn.MaxPool2d((2,1)))
        s.f = nn.Sequential(blk(1,64), blk(64,128), blk(128,256), nn.Flatten(), nn.Dropout(0.5))
        s.head = nn.Linear(256*(H//8)*W, 2)
    def forward(s,x): return s.head(s.f(x))

torch.manual_seed(0); m = CNN().to(dev)
for p_ in m.parameters():
    if p_.dim() > 1: nn.init.xavier_uniform_(p_)          # JKX: Xavier
print(f"{sum(p.numel() for p in m.parameters()):,} parameters")"""))

C.append(MD("""## 6. Train

Mixed precision — fp32 on a T4 is ~21 min/epoch over the full panel, which would
exceed Colab's idle timeout before early stopping fires. Patience 2, as in JKX."""))
C.append(CO("""EPOCHS, PATIENCE, BS = 20, 2, 256
opt = torch.optim.Adam(m.parameters(), lr=1e-5)
lossf = nn.CrossEntropyLoss()
scaler = torch.amp.GradScaler("cuda", enabled=(dev=="cuda"))
dl_tr = torch.utils.data.DataLoader(DS(X[i_tr],Y[i_tr],MU,SD), batch_size=BS,
                                    shuffle=True, num_workers=2, drop_last=True, pin_memory=True)
dl_va = torch.utils.data.DataLoader(DS(X[i_va],Y[i_va],MU,SD), batch_size=1024,
                                    num_workers=2, pin_memory=True)
best, bad = 1e9, 0
for ep in range(EPOCHS):
    t0 = time.time(); m.train()
    for xb,yb in dl_tr:
        xb,yb = xb.to(dev,non_blocking=True), yb.to(dev,non_blocking=True)
        opt.zero_grad(set_to_none=True)
        with torch.amp.autocast("cuda", enabled=(dev=="cuda")): loss = lossf(m(xb), yb)
        scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
    m.eval(); vl = n = 0
    with torch.no_grad(), torch.amp.autocast("cuda", enabled=(dev=="cuda")):
        for xb,yb in dl_va:
            xb,yb = xb.to(dev,non_blocking=True), yb.to(dev,non_blocking=True)
            vl += lossf(m(xb),yb).item()*len(yb); n += len(yb)
    vl /= n
    print(f"epoch {ep+1:2d}  val loss {vl:.5f}  ({time.time()-t0:.0f}s)"+("  *" if vl<best else ""), flush=True)
    if vl < best: best, bad = vl, 0; torch.save(m.state_dict(), "best.pt")
    else:
        bad += 1
        if bad >= PATIENCE: print("early stop"); break
m.load_state_dict(torch.load("best.pt")); m.eval(); print(f"best val loss {best:.5f}")"""))

C.append(MD("""## 7. Is the instrument any good? (strictly out of sample)"""))
C.append(CO("""def predict_packed(Xp, bs=2048):
    out = []
    dl = torch.utils.data.DataLoader(DS(Xp, np.zeros(len(Xp),dtype=np.int64), MU, SD),
                                     batch_size=bs, num_workers=2, pin_memory=True)
    with torch.no_grad(), torch.amp.autocast("cuda", enabled=(dev=="cuda")):
        for xb,_ in dl: out.append(torch.softmax(m(xb.to(dev)).float(),1)[:,1].cpu().numpy())
    return np.concatenate(out)

p_te, y_te = predict_packed(X[i_te]), Y[i_te]
n1, n0 = (y_te==1).sum(), (y_te==0).sum()
auc = (stats.rankdata(p_te)[y_te==1].sum() - n1*(n1+1)/2)/(n1*n0)
print(f"test accuracy {((p_te>0.5)==(y_te==1)).mean():.4f}  (base {max(y_te.mean(),1-y_te.mean()):.4f})")
print(f"test AUC      {auc:.4f}")
print(f"corr(pred, up) {np.corrcoef(p_te, y_te)[0,1]:+.4f}")
if auc < 0.51:
    print("\\nWARNING: the CNN barely beats chance out of sample.  A weak instrument")
    print("cannot distinguish 'patterns carry nothing' from 'model learned nothing'.")"""))

C.append(MD("""## 8. THE CONTROL — Brownian motion must return ~50%

Simulated images are rendered by the **same `render()`** as real ones, with real
volume profiles and an MA line, so nothing but the price path differs. Paths run
2*NDAYS long because a 20-day MA needs 20 prior days."""))
C.append(CO("""vol_pool = []
for _s,_g in df.groupby("symbol", sort=False):
    _v = _g.volume.values.astype(np.float64)
    for _i in range(NDAYS, len(_v), 97):
        _w = _v[_i-NDAYS:_i]
        if np.isfinite(_w).all() and _w.max() > 0: vol_pool.append(_w/_w.max())
vol_pool = np.array(vol_pool)
print(f"real volume profiles for simulation: {len(vol_pool):,}")

SIGMA = 0.02
def images_from_paths(paths, rng):
    '''(n, 2*NDAYS) close paths -> packed images of their LAST NDAYS'''
    ma = pd.DataFrame(paths.T).rolling(MA_WIN).mean().values.T
    C_ = paths[:, NDAYS:]; M = ma[:, NDAYS:]
    O  = np.concatenate([paths[:, NDAYS-1:NDAYS], C_[:, :-1]], 1)
    sp = np.abs(C_-O)*0.5 + np.abs(C_).mean(1, keepdims=True)*0.004
    Hh = np.maximum(O,C_) + sp*rng.random(C_.shape)
    L  = np.minimum(O,C_) - sp*rng.random(C_.shape)
    V  = vol_pool[rng.integers(len(vol_pool), size=len(C_))]
    img, ok = render(O, Hh, L, C_, V, M)
    return np.packbits(img[ok].reshape(ok.sum(), -1) > 0, axis=1)

def probe(path_fn, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    return predict_packed(images_from_paths(path_fn(rng, n), rng))

brown = probe(lambda r,n: np.cumprod(1 + r.normal(0, SIGMA, (n, 2*NDAYS)), axis=1))
t_, p_ = stats.ttest_1samp(brown, 0.5)
print(f"\\nBrownian control: mean P(up) = {brown.mean():.4f} (sd {brown.std():.4f})")
print(f"  vs 0.50 -> t = {t_:+.2f}, p = {p_:.3g}")
OK = abs(brown.mean()-0.5) < 0.03
print("\\nPLACEBO " + ("PASSED - instrument usable" if OK else
      "FAILED - the CNN is biased; nothing below is interpretable"))
assert OK, "placebo failed - do not interpret what follows"
"""))

C.append(MD("""## 9. The 23 textbook patterns

`+1` = the books call it bullish, `-1` = bearish. Shapes are piecewise-linear
control points; **inspect the plot** — a surprising result may be a claim about
the drawing rather than the pattern."""))
C.append(CO("""def seg(pts, n): return np.interp(np.linspace(0,len(pts)-1,n), np.arange(len(pts)), pts)

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
fig, ax = plt.subplots(4,6, figsize=(15,8))
for a,(nm,pts,d) in zip(ax.ravel(), PATTERNS):
    a.plot(seg(pts,60), color="green" if d>0 else "red", lw=1.5)
    a.set_title(nm, fontsize=7); a.set_xticks([]); a.set_yticks([])
for a in ax.ravel()[len(PATTERNS):]: a.axis("off")
plt.tight_layout(); plt.show()"""))

C.append(MD("## 10. Run the probe"))
C.append(CO("""NOISE, AMP_ = 0.35, 0.10
def path_fn_for(pts):
    def f(rng, n):
        lead = rng.normal(0, SIGMA*NOISE, (n, NDAYS)).cumsum(1)
        base = (seg(pts, NDAYS)[None,:]*AMP_*rng.uniform(.7,1.3,(n,1))
                + rng.normal(0, SIGMA*NOISE, (n, NDAYS)).cumsum(1) + lead[:,-1:])
        full = np.concatenate([lead, base], 1)
        return np.cumprod(1+np.diff(np.concatenate([np.zeros((n,1)), full],1), axis=1), axis=1)
    return f

rows = []
for i,(nm,pts,d) in enumerate(PATTERNS):
    p = probe(path_fn_for(pts), n=10000, seed=100+i)
    t_,p_ = stats.ttest_ind(p, brown, equal_var=False)
    rows.append(dict(pattern=nm, folk=d, mean_p_up=p.mean(),
                     vs_brownian=p.mean()-brown.mean(), t=t_, p=p_))
    print(f"  {nm:30s} P(up)={p.mean():.4f}  t={t_:+7.2f}", flush=True)

R = pd.DataFrame(rows)
ALPHA = 0.01/len(PATTERNS)
R["significant"] = R.p < ALPHA
R["cnn_dir"] = np.sign(R.vs_brownian)
R["agrees_with_books"] = R.significant & (R.cnn_dir == R.folk)
R["INVERTED"] = R.significant & (R.cnn_dir == -R.folk)
R.sort_values("vs_brownian", ascending=False)"""))

C.append(MD("## 11. Verdict"))
C.append(CO("""n_sig, n_ok, n_inv = int(R.significant.sum()), int(R.agrees_with_books.sum()), int(R.INVERTED.sum())
print(f"Bonferroni alpha = {ALPHA:.5f} over {len(PATTERNS)} patterns\\n")
print(f"  significant             : {n_sig} of {len(PATTERNS)}")
print(f"  ... as the books claim   : {n_ok}")
print(f"  ... INVERTED             : {n_inv}")
print(f"  not distinguishable      : {len(PATTERNS)-n_sig}")
print(f"\\nJKX, US daily 1993-2019: 13 of 23 significant, 8 of those inverted ({8/13:.0%}).")
if n_sig: print(f"here: {n_inv}/{n_sig} inverted ({n_inv/n_sig:.0%})")

s = R.sort_values("vs_brownian")
col = ["#c0392b" if i else ("#27ae60" if o else "#bdc3c7")
       for i,o in zip(s.INVERTED, s.agrees_with_books)]
fig, a = plt.subplots(figsize=(9,7))
a.barh(s.pattern, s.vs_brownian, color=col); a.axvline(0, color="k", lw=.8)
a.set_xlabel("CNN P(up) minus Brownian control")
a.set_title("green = matches the books   red = inverted   grey = not significant")
plt.tight_layout(); plt.show()"""))

C.append(MD("""## What this establishes, and what it does not

**Does.** Whether a CNN trained on a survivorship-inclusive panel assigns the
textbook patterns the direction the textbooks claim — with a Brownian placebo
proving the instrument is not merely biased, Bonferroni control over 23
simultaneous tests, and real and synthetic images rendered by identical code.

**Does not.** Daily bars, so silent on 5-minute charts. A directional
association is not a strategy — every result in this project has died at the
cost step, not the signal step. And the CNN is an instrument, not ground truth:
a pattern it cannot see might still matter.

**Read the test AUC in cell 7 before believing cell 11.** A weak instrument
cannot distinguish "the patterns carry nothing" from "the model learned
nothing."""))

nb={"cells":C,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},
    "language_info":{"name":"python"},"accelerator":"GPU","colab":{"provenance":[],"gpuType":"T4"}},
    "nbformat":4,"nbformat_minor":0}
p="exploration/colab/chart_patterns_colab.ipynb"
json.dump(nb, open(p,"w"), indent=1)
print(f"wrote {p}: {len(C)} cells")
