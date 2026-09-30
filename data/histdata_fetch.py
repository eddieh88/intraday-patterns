"""Download HistData.com free spot FX tick quotes (bid/ask, ms timestamps) and reduce
each month to 1-minute bars:
  bid open/high/low/close, ask open/high/low/close, spread mean/max (pips), tick count
-> cache/histdata/<pair>_<YYYYMM>.parquet, column `ts_ny`: New York local time (bar start).

HistData documents its timestamps as EST without daylight saving, but US payroll
releases (8:30 ET) appear at 08:30 in both winter and summer: the timestamps are New
York local time WITH daylight saving. Checked 2026-09-30 on four 2021 payroll days.

Resumable (finished months are skipped) and polite (one request every few seconds).
Months before 2015 belong to the sealed early period (see lib/holdout.py) -- this
script only downloads and aggregates them; it never prints anything about prices.

  python3 data/histdata_fetch.py                    # dev years first, then early years
  python3 data/histdata_fetch.py eurgbp 2024 3      # one month
  python3 data/histdata_fetch.py --pairs eurgbp,eurchf   # a subset (run several in parallel)
"""
import io, sys, time, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import requests

PAIRS = ["eurgbp", "eurchf", "audnzd", "eurusd", "gbpusd", "audusd", "nzdusd", "usdjpy"]
OUT = Path("cache/histdata")
UA = {"User-Agent": "Mozilla/5.0"}
PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/tick-data-quotes/{p}/{y}/{m}"


def pip(pair):
    return 0.01 if pair.endswith("jpy") else 0.0001


def fetch(pair, y, m, s):
    dest = OUT / f"{pair}_{y}{m:02d}.parquet"
    if dest.exists():
        return "skip"
    url = PAGE.format(p=pair, y=y, m=m)
    html = s.get(url, headers=UA, timeout=60).text
    if 'name="tk"' not in html:
        return "no page"
    tk = html.split('name="tk" id="tk" value="')[1].split('"')[0]
    r = s.post("https://www.histdata.com/get.php", headers={**UA, "Referer": url}, timeout=300,
               data={"tk": tk, "date": str(y), "datemonth": f"{y}{m:02d}", "platform": "ASCII",
                     "timeframe": "T", "fxpair": pair.upper()})
    if r.status_code != 200 or r.content[:2] != b"PK":
        return f"no data ({r.status_code})"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = next(n for n in z.namelist() if n.endswith(".csv"))
    d = pd.read_csv(z.open(name), header=None, names=["t", "bid", "ask", "v"],
                    dtype={"t": str, "bid": float, "ask": float})
    d["t"] = pd.to_datetime(d.t, format="%Y%m%d %H%M%S%f")          # New York local time
    d["sp"] = (d.ask - d.bid) / pip(pair)
    g = d.set_index("t").resample("1min", label="left", closed="left")
    bars = pd.concat([g.bid.ohlc().add_prefix("bid_"), g.ask.ohlc().add_prefix("ask_"),
                      g.sp.mean().rename("spread_mean"), g.sp.max().rename("spread_max"),
                      g.bid.count().rename("ticks")], axis=1)
    bars = bars[bars.ticks > 0].astype({"ticks": "int32"})
    bars.index.name = "ts_ny"
    tmp = dest.with_suffix(".tmp")
    bars.reset_index().to_parquet(tmp, index=False)
    tmp.rename(dest)
    return f"{len(bars):,} minutes"


def months(years):
    today = pd.Timestamp.today()
    for y in years:
        for m in range(1, 13):
            if pd.Timestamp(y, m, 1) < today.replace(day=1):
                yield y, m


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    if len(sys.argv) == 3 and sys.argv[1] == "--pairs":
        PAIRS = sys.argv[2].split(",")
    if len(sys.argv) == 4:
        jobs = [(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))]
    else:
        order = list(range(2021, 2027)) + list(range(2020, 2009, -1))    # dev first, then early
        jobs = [(p, y, m) for years in ([y] for y in order) for p in PAIRS for y, m in months(years)]
    for pair, y, m in jobs:
        for attempt in range(3):
            try:
                msg = fetch(pair, y, m, s)
                break
            except (requests.RequestException, zipfile.BadZipFile, OSError) as e:
                msg = f"error {type(e).__name__}"
                time.sleep(30 * (attempt + 1))
        print(f"{pair} {y}-{m:02d}: {msg}", flush=True)
        if msg != "skip":
            time.sleep(3)
