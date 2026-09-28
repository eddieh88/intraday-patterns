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
