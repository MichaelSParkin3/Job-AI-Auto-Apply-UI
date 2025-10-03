"""Contract tests for the `apply` CLI command."""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterable, Iterator
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate

from job_ai_auto_apply_ui.orchestrator import main


def _run_cli(args: Iterable[str]) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.fixture()
def apply_schema() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = (
        repo_root / "specs" / "001-as-a-job" / "contracts" / "schemas" / "apply-event.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_apply_json_stream_success(
    monkeypatch: pytest.MonkeyPatch, apply_schema: dict[str, Any]
) -> None:
    """Streaming JSON events should match schema and exit code should be zero on success."""
    events: list[dict[str, Any]] = [
        {"event": "start", "profile": "front_end"},
        {"event": "item", "id": "item-1", "status": "in_progress"},
        {"event": "submitted", "id": "item-1", "confirmation_id": "CONF-123"},
        {"event": "end", "summary": {"submitted": 1, "failed": 0}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, Any]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: dict[str, Any], mode: str) -> Iterator[dict[str, Any]]:
        assert mode == "supervised"
        yield from events

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.orchestrator.iter_apply_events", fake_iter_apply_events
    )

    code, out, err = _run_cli(["apply", "--profile", "front_end", "--json"])

    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == len(events)
    for raw in lines:
        payload = json.loads(raw)
        validate(instance=payload, schema=apply_schema)
    assert err == ""


def test_apply_json_partial_failure(
    monkeypatch: pytest.MonkeyPatch, apply_schema: dict[str, Any]
) -> None:
    """If any item fails the command exits with code 3."""
    events: list[dict[str, Any]] = [
        {"event": "start", "profile": "front_end"},
        {"event": "item", "id": "item-1", "status": "in_progress"},
        {
            "event": "failed",
            "id": "item-1",
            "reason": {"code": "captcha_blocked", "message": "Encountered hCaptcha"},
        },
        {"event": "end", "summary": {"submitted": 0, "failed": 1}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, Any]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: dict[str, Any], mode: str) -> Iterator[dict[str, Any]]:
        yield from events

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.orchestrator.iter_apply_events", fake_iter_apply_events
    )

    code, out, err = _run_cli(["apply", "--profile", "front_end", "--json", "--auto"])

    assert code == 3
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == len(events)
    for raw in lines:
        payload = json.loads(raw)
        validate(instance=payload, schema=apply_schema)
    assert err == ""
