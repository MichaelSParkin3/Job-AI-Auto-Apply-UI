"""Pytest configuration for the project."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository root (which contains the ``src`` package) is on ``sys.path``.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
