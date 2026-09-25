# data

Fetchers for the MarketParquet archive, plus the one build step every
experiment depends on.

| file | |
|---|---|
| `mp5_fetch.py` | 5-minute equity bars → `cache/mp5min/` — **this is the one the experiments use** |
| `build_daily.py` | One daily summary table from that archive → `cache/intraday_daily.parquet`. Run once before any experiment. |
| `minute_fetch.py` | 5-minute bars for the pre-registered sample days (earlier, narrower pull) |
| `mp_etf_5min_fetch.py` | ETF 5-minute bars (3.2 GB) — **downloaded, never used in any test** |
| `mp_futures_5min_fetch.py` | Futures 5-minute bars (511 MB, ES verified back-adjusted) — **never used** |
| `mp_futures_1min_fetch.py` | Futures 1-minute bars (1.4 GB) — **never used** |
| `mp_validate.py` | The pre-purchase gate. Sales are final, so this had to be decisive before buying. |

The futures and ETF archives are the largest untested opportunity in this
repository: almost every setting tested here is taught on ES, NQ and SPY, and
every test ran on single stocks.

## Setup

```bash
python3 data/mp5_fetch.py     # then
python3 data/build_daily.py
```

Needs a MarketParquet key at `~/.market_parquest/api_key.txt` — never in the
repo. If you already hold the archive, `ln -s /path/to/cache cache` instead.
