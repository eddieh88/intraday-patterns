import importlib.util
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mp_fetch", ROOT / "data" / "mp_fetch.py")
mp_fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mp_fetch)


class _Response:
    def __init__(self, content, status=200):
        self.content, self.status = content, status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"status {self.status}")


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(mp_fetch.time, "sleep", lambda s: None)


def test_complete_download_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(mp_fetch.requests, "get", lambda *a, **k: _Response(b"x" * 5000))
    n = mp_fetch.grab({"filename": "f.parquet", "download_url": "u"}, str(tmp_path))
    assert n == 5000 and (tmp_path / "f.parquet").stat().st_size == 5000
    assert not list(tmp_path.glob("*.part"))


def test_failed_download_leaves_no_file(tmp_path, monkeypatch):
    def fail(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(mp_fetch.requests, "get", fail)
    assert mp_fetch.grab({"filename": "f.parquet", "download_url": "u"}, str(tmp_path)) == 0
    assert not list(tmp_path.iterdir())


def test_interrupted_write_leaves_no_final_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mp_fetch.requests, "get", lambda *a, **k: _Response(b"x" * 5000))
    def crash(src, dst):
        raise OSError("disk full")
    monkeypatch.setattr(mp_fetch.os, "replace", crash)
    mp_fetch.grab({"filename": "f.parquet", "download_url": "u"}, str(tmp_path))
    assert not (tmp_path / "f.parquet").exists()


def test_error_pages_are_not_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(mp_fetch.requests, "get", lambda *a, **k: _Response(b"<html>", 200))
    assert mp_fetch.grab({"filename": "f.parquet", "download_url": "u"}, str(tmp_path)) == 0
    assert not (tmp_path / "f.parquet").exists()


def test_unknown_dataset_is_rejected():
    with pytest.raises(SystemExit):
        mp_fetch.main("stock_1sec")
