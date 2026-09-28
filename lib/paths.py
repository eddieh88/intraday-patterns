"""Repository paths, independent of the directory a script is run from.

    from paths import ROOT, add_to_path
    add_to_path("selection")          # import sibling modules such as session_summary

Data paths in the experiments ("cache/...", "colab/...") are still relative to the
repository root, so run scripts from there (see README).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def add_to_path(*folders: str) -> None:
    """Put repository folders on sys.path, resolved from the repo root rather than the cwd."""
    for folder in folders:
        path = str(ROOT / folder)
        if path not in sys.path:
            sys.path.insert(0, path)
