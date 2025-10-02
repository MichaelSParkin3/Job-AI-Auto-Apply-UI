"""Pytest configuration for the project."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"


def _ensure_path(path: Path) -> None:
    """Insert ``path`` into ``sys.path`` ahead of imports if missing."""

    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)


_ensure_path(PROJECT_ROOT)
_ensure_path(SRC_ROOT)
