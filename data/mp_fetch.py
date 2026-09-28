"""Download a MarketParquet intraday archive.

Uses the manifest endpoint (up to 400 files per call, presigned R2 URLs) rather
than one request per day. Files are cached under cache/<folder>/ and skipped if
already present, so this is resumable -- kill it and re-run. Each file is written
to a temporary name and renamed only when complete, so an interrupted download
never leaves a truncated file that a later run would mistake for a finished one.

  python3 data/mp_fetch.py stock_5min                # from 2021-01-04 to today
  python3 data/mp_fetch.py stock_5min 2017-01-01     # from a date
  python3 data/mp_fetch.py futures_1min 2021-01-04 2024-12-31

Needs a key at ~/.market_parquest/api_key.txt (never in the repo).
"""
import os, sys, time
import requests
from concurrent.futures import ThreadPoolExecutor

KEY  = os.path.expanduser("~/.market_parquest/api_key.txt")
BASE = "https://marketparquet.com/api/v1"
# dataset -> cache folder (folder names kept from the original per-dataset scripts)
DATASETS = {
    "stock_5min":   "cache/mp5min",        # the archive the experiments use
    "etf_5min":     "cache/mp_etf_5min",
    "futures_5min": "cache/mp_futures_5min",
    "futures_1min": "cache/mp_futures_1min",
}
CHUNK_DAYS = 300          # manifest caps at 400 files
WORKERS    = 8            # paid tier allows 600 req/min
MIN_BYTES  = 1000         # anything smaller is an error page, not a parquet file

def hdrs():
    if not os.path.exists(KEY):
        sys.exit(f"no key at {KEY}")
    with open(KEY) as f:
        return {"Authorization": f"Bearer {f.read().strip()}"}

def manifest(h, dataset, start, end):
    r = requests.get(f"{BASE}/manifest/{dataset}",
                     params={"start": start, "end": end}, headers=h, timeout=120)
    r.raise_for_status()
    return r.json().get("files", [])

def grab(item, out):
    dst = os.path.join(out, item["filename"])
    if os.path.exists(dst) and os.path.getsize(dst) > MIN_BYTES:
        return 0
    error = None
    for attempt in range(3):
        try:
            r = requests.get(item["download_url"], timeout=180)
            r.raise_for_status()
            if len(r.content) > MIN_BYTES:
                tmp = dst + ".part"
                with open(tmp, "wb") as f:
                    f.write(r.content)
                os.replace(tmp, dst)      # atomic: dst is either absent or complete
                return len(r.content)
            error = f"only {len(r.content)} bytes"
        except (requests.RequestException, OSError) as e:
            error = f"{type(e).__name__}: {e}"
        time.sleep(1 + attempt)
    print(f"  FAILED {item['filename']} ({error})", flush=True)
    return 0

def main(dataset, start="2021-01-04", end=None):
    import pandas as pd
    if dataset not in DATASETS:
        sys.exit(f"unknown dataset {dataset!r}; choose from {', '.join(DATASETS)}")
    out = DATASETS[dataset]
    os.makedirs(out, exist_ok=True)
    h = hdrs()
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    edges = pd.date_range(start, end, freq=f"{CHUNK_DAYS}D").tolist()
    if pd.Timestamp(end) > edges[-1]: edges.append(pd.Timestamp(end))
    t0, got, byt = time.time(), 0, 0
    for a, b in zip(edges[:-1], edges[1:]):
        files = manifest(h, dataset, a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d"))
        have = sum(1 for f in files
                   if os.path.exists(os.path.join(out, f["filename"])))
        with ThreadPoolExecutor(WORKERS) as ex:
            byt += sum(ex.map(lambda item: grab(item, out), files))
        got += len(files)
        print(f"  {a.date()}..{b.date()}  {len(files):3d} files "
              f"({have} cached)  total {got:5d}  {byt/1e6:7.1f} MB  "
              f"{time.time()-t0:5.0f}s", flush=True)
    n = len([f for f in os.listdir(out) if f.endswith('.parquet')])
    print(f"\ndone: {n} daily files in {out}/  ({byt/1e6:.0f} MB downloaded)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:])
