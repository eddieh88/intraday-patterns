# data

Fetchers for the MarketParquet archive, plus the one build step every
experiment depends on.

| file | |
|---|---|
| `mp_fetch.py` | Downloads any MarketParquet intraday archive: `python3 data/mp_fetch.py <dataset>`, with dataset `stock_5min` (→ `cache/mp5min/`, **the one the experiments use**), `etf_5min`, `futures_5min` or `futures_1min`. Resumable; files are written atomically. |
| `histdata_fetch.py` | Free HistData.com spot FX tick quotes (bid/ask), reduced to 1-minute bid/ask bars with spread stats → `cache/histdata/`. 8 pairs, 2010 on. Read with `explore_own/data.py`; pre-2021 is sealed (`lib/holdout.py`). |
| `build_daily.py` | One daily summary table from that archive → `cache/intraday_daily.parquet`, plus the point-in-time universe → `cache/intraday_pool.parquet`. Run once before any experiment. |
| `universe_check.py` | Regression test: rebuilds the universe from files truncated at the day before and requires an exact match. **Run it before trusting any result.** |
| `mp_validate.py` | The pre-purchase gate. Sales are final, so this had to be decisive before buying. |

Archive sizes: ETF 5-minute bars 3.2 GB (read by `selection/session_summary.py`);
futures 5-minute bars 511 MB (ES verified back-adjusted; used by `explore_fut/`);
futures 1-minute bars 1.4 GB (used by `explore_nq/`); futures 5-minute bars for
2008–2020 in `cache/mp_futures_5min_early/` (sealed early period, `mp_fetch.py`'s
4th argument).

## Setup

```bash
python3 data/mp_fetch.py stock_5min   # then
python3 data/build_daily.py
python3 data/universe_check.py
```

Needs a MarketParquet key at `~/.market_parquest/api_key.txt` — never in the
repo. If you already hold the archive, `ln -s /path/to/cache cache` instead.
