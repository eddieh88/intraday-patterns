import importlib

import pandas as pd
import pytest

import holdout


def test_development_drops_holdout_rows():
    df = pd.DataFrame({"date": ["2025-03-31", "2025-04-01", "2026-01-02"]})
    assert list(holdout.development(df)["date"]) == ["2025-03-31"]


def test_assert_sealed_raises_on_holdout_dates(monkeypatch):
    monkeypatch.delenv("HOLDOUT_UNLOCK", raising=False)
    sealed = importlib.reload(holdout)
    with pytest.raises(RuntimeError, match="sealed holdout"):
        sealed.assert_sealed(["2024-12-31", "2025-04-01"])


def test_assert_sealed_passes_development_dates():
    assert len(holdout.assert_sealed(["2024-01-02", "2025-03-31"])) == 2


def test_unlock_requires_the_exact_phrase(monkeypatch):
    monkeypatch.setenv("HOLDOUT_UNLOCK", "yes")
    with pytest.raises(RuntimeError):
        importlib.reload(holdout).assert_sealed(["2025-06-01"])
    monkeypatch.setenv("HOLDOUT_UNLOCK", "final-evaluation")
    assert len(importlib.reload(holdout).assert_sealed(["2025-06-01"])) == 1
    monkeypatch.delenv("HOLDOUT_UNLOCK")
    importlib.reload(holdout)


def test_early_period_is_sealed_separately(monkeypatch):
    monkeypatch.delenv("EARLY_UNLOCK", raising=False)
    monkeypatch.setenv("HOLDOUT_UNLOCK", "final-evaluation")      # the other switch doesn't open it
    h = importlib.reload(holdout)
    with pytest.raises(RuntimeError, match="sealed early period"):
        h.assert_early_sealed(["2014-12-31", "2015-01-02"])
    assert len(h.assert_early_sealed(["2015-01-02"])) == 1
    monkeypatch.setenv("EARLY_UNLOCK", "final-evaluation")
    assert len(importlib.reload(holdout).assert_early_sealed(["2012-01-15"])) == 1
    monkeypatch.delenv("EARLY_UNLOCK")
    monkeypatch.delenv("HOLDOUT_UNLOCK")
    importlib.reload(holdout)


def test_histdata_loader_refuses_early_files(tmp_path, monkeypatch):
    """explore_own/data.py must not return pre-2021 bars unless EARLY_UNLOCK is set."""
    import sys
    monkeypatch.delenv("EARLY_UNLOCK", raising=False)
    importlib.reload(holdout)
    (tmp_path / "cache" / "histdata").mkdir(parents=True)
    t = pd.date_range("2014-12-31 20:00", periods=3, freq="1min")
    cols = {f"{s}_{c}": 1.0 for s in ("bid", "ask") for c in ("open", "high", "low", "close")}
    pd.DataFrame({"ts_ny": t, **cols, "spread_mean": 1.0, "spread_max": 1.0, "ticks": 1}).to_parquet(
        tmp_path / "cache" / "histdata" / "eurgbp_201412.parquet")
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(holdout.__file__).rsplit("/lib/", 1)[0] + "/explore_own")
    import data as own_data
    importlib.reload(own_data)
    with pytest.raises(RuntimeError, match="sealed early period"):
        own_data.load("eurgbp", "early")
    with pytest.raises(FileNotFoundError):
        own_data.load("eurgbp", "dev")
