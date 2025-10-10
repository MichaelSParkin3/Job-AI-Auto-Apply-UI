"""SavedState v1 schema and JSON I/O helpers for form state persistence."""

from __future__ import annotations

import json
from pathlib import Path


def write_pre_state(path: Path, payload: dict) -> None:
    """Write SavedState v1 payload to pre.json.

    Args:
        path: Filesystem path where pre.json should be written.
        payload: SavedState v1 dictionary containing version, timestamps, plan, values, and labels.

    Raises:
        OSError: If the file cannot be written.

    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_pre_state(path: Path) -> dict:
    """Read SavedState v1 payload from pre.json.

    Args:
        path: Filesystem path to pre.json file.

    Returns:
        dict: SavedState v1 dictionary with version, timestamps, plan, values, and optional labels.

    Raises:
        FileNotFoundError: If pre.json does not exist at the specified path.
        json.JSONDecodeError: If the file contains invalid JSON.

    """
    content = path.read_text(encoding="utf-8")
    return json.loads(content)
