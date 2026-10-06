import importlib
import sys
import warnings

import paths


def test_add_to_path_resolves_from_repo_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                       # somewhere that is not the repo
    sel = str(paths.ROOT / "selection")
    # start without selection/: another test module may already have added it at import
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != sel])
    paths.add_to_path("selection")
    assert str(paths.ROOT / "selection") == sys.path[0]
    paths.add_to_path("selection")                    # idempotent
    assert sys.path.count(str(paths.ROOT / "selection")) == 1


def test_importing_lib_has_no_global_side_effects():
    filters, path = list(warnings.filters), list(sys.path)
    for name in ("swing_levels", "setups_v2", "r_multiple", "intraday_levels", "holdout"):
        importlib.reload(importlib.import_module(name))
    assert warnings.filters == filters
    assert sys.path == path
