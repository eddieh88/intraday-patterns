"""Download the MarketParquet 5-MINUTE archive.

Uses the manifest endpoint (up to 400 files per call, presigned R2 URLs) rather
than one request per day.  Files are cached under cache/mp/ and skipped if
already present, so this is resumable -- kill it and re-run.

  python3 src/mp_fetch.py              # everything from 2000-01-03
  python3 src/mp_fetch.py 2017-01-01   # from a date
"""
import os, sys, json, time
import requests
from concurrent.futures import ThreadPoolExecutor

KEY  = os.path.expanduser("~/.market_parquest/api_key.txt")
BASE = "https://marketparquet.com/api/v1"
OUT  = "cache/mp5min"
CHUNK_DAYS = 300          # manifest caps at 400 files
WORKERS    = 8            # paid tier allows 600 req/min

def hdrs():
    if not os.path.exists(KEY):
        sys.exit(f"no key at {KEY}")
    return {"Authorization": f"Bearer {open(KEY).read().strip()}"}

def manifest(h, start, end):
    r = requests.get(f"{BASE}/manifest/stock_5min",
                     params={"start": start, "end": end}, headers=h, timeout=120)
    r.raise_for_status()
    return r.json().get("files", [])

def grab(item):
    dst = os.path.join(OUT, item["filename"])
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return 0
    for attempt in range(3):
        try:
            b = requests.get(item["download_url"], timeout=180).content
            if len(b) > 1000:
                open(dst, "wb").write(b); return len(b)
        except Exception:
            time.sleep(1 + attempt)
    print("  FAILED", item["filename"], flush=True)
    return 0

def main(start="2021-01-04", end=None):
    import pandas as pd
    os.makedirs(OUT, exist_ok=True)
    h = hdrs()
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    edges = pd.date_range(start, end, freq=f"{CHUNK_DAYS}D").tolist()
    if pd.Timestamp(end) > edges[-1]: edges.append(pd.Timestamp(end))
    t0, got, byt = time.time(), 0, 0
    for a, b in zip(edges[:-1], edges[1:]):
        files = manifest(h, a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d"))
        have = sum(1 for f in files
                   if os.path.exists(os.path.join(OUT, f["filename"])))
        with ThreadPoolExecutor(WORKERS) as ex:
            byt += sum(ex.map(grab, files))
        got += len(files)
        print(f"  {a.date()}..{b.date()}  {len(files):3d} files "
              f"({have} cached)  total {got:5d}  {byt/1e6:7.1f} MB  "
              f"{time.time()-t0:5.0f}s", flush=True)
    n = len([f for f in os.listdir(OUT) if f.endswith('.parquet')])
    print(f"\ndone: {n} daily files in {OUT}/  ({byt/1e6:.0f} MB downloaded)")

if __name__ == "__main__":
    main(*sys.argv[1:])
