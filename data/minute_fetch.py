"""Download 5-minute bars for the pre-registered sample days.

1-minute would be 10GB for 500 days; 5-minute is ~3.5GB and sufficient -- 15:45
falls on a bar boundary and the pre-registered session split is at noon.
Sub-hourly tests are ruled out in advance (bid-ask bounce), so finer bars would
add nothing usable.
"""
import os, sys, time, requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

KEY  = os.path.expanduser("~/.market_parquest/api_key.txt")
BASE = "https://marketparquet.com/api/v1"
OUT  = "cache/mp5"
ASSET = "stock_5min"

def hdrs(): return {"Authorization": f"Bearer {open(KEY).read().strip()}"}

def grab(args):
    d, h = args
    dst = f"{OUT}/{ASSET}_{d}.parquet"
    if os.path.exists(dst) and os.path.getsize(dst) > 10000: return 0
    for a in range(3):
        try:
            r = requests.get(f"https://marketparquet.com/api/data/download/{ASSET}/{d}.parquet",
                             headers=h, timeout=240)
            if r.status_code == 200 and len(r.content) > 10000:
                open(dst, "wb").write(r.content); return len(r.content)
            if r.status_code == 404: return 0
        except Exception:
            time.sleep(1 + a)
    print("  FAILED", d, flush=True)
    return 0

def main():
    os.makedirs(OUT, exist_ok=True)
    h = hdrs()
    days = [l.strip() for l in open("cache/minute_sample.csv") if l.strip()]
    print(f"{len(days)} sample days", flush=True)
    t0, tot = time.time(), 0
    for i in range(0, len(days), 50):
        chunk = days[i:i+50]
        with ThreadPoolExecutor(6) as ex:
            tot += sum(ex.map(grab, [(d, h) for d in chunk]))
        n = len([f for f in os.listdir(OUT) if f.endswith(".parquet")])
        print(f"  {chunk[0]}..{chunk[-1]}  cached {n:4d}/{len(days)}  "
              f"{tot/1e9:.2f} GB  {time.time()-t0:5.0f}s", flush=True)
    print(f"\ndone: {len([f for f in os.listdir(OUT) if f.endswith('.parquet')])} files")

if __name__ == "__main__":
    main()
