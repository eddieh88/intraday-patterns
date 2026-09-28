"""Runs selection/test_audit.py (the timestamp audit) when the data cache is present.

Takes about two minutes; skip it for a quick commit with SKIP_DATA_TESTS=1.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NEEDED = ["cache/mp5min", "cache/sel_stocks.parquet", "cache/sel_etfs.parquet",
          "cache/intraday_pool.parquet", "cache/sel_features.parquet"]


@pytest.mark.skipif(os.environ.get("SKIP_DATA_TESTS") == "1", reason="SKIP_DATA_TESTS=1")
@pytest.mark.skipif(not all((ROOT / p).exists() for p in NEEDED),
                    reason="needs the MarketParquet cache (see data/README.md)")
def test_timestamp_audit_passes():
    result = subprocess.run([sys.executable, "selection/test_audit.py"], cwd=ROOT,
                            capture_output=True, text=True, timeout=3600)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
