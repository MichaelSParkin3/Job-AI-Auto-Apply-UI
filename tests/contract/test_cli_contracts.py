"""CLI contract smoke tests that exercise high-level orchestrator flows."""

from __future__ import annotations

import contextlib
import importlib
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Iterable

import pytest
from jsonschema import validate


def _load_orchestrator() -> Any:
    """Import the orchestrator lazily without pulling heavy browser modules."""

    for name in (
        "job_ai_auto_apply_ui.browser_agent",
        "job_ai_auto_apply_ui.browser_agent.lever",
        "job_ai_auto_apply_ui.orchestrator",
    ):
        sys.modules.pop(name, None)
    module = importlib.import_module("job_ai_auto_apply_ui.orchestrator")
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules
    return module


@pytest.fixture()
def orchestrator_module() -> Any:
    return _load_orchestrator()


def _run_cli(
    module: Any, args: Iterable[str], monkeypatch: pytest.MonkeyPatch
) -> tuple[int, str, str]:
    """Execute CLI entrypoint with environment isolation and captured stdio."""

    monkeypatch.setenv("AUTO_APPLY_BROWSER_MODE", "off")
    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


def test_discover_json_contract_no_results(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    def fake_load_profile(profile_id: str) -> dict[str, str]:
        return {"id": profile_id, "name": profile_id.title()}

    def fake_discover(profile: dict[str, str], window_hours: int, cap: int) -> list[Any]:
        return []

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.job_discovery.discover_jobs", fake_discover
    )

    code, out, err = _run_cli(
        orchestrator_module, ["discover", "--profile", "dev", "--json"], monkeypatch
    )

    assert code == 2
    payload = json.loads(out)
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo / "specs" / "001-as-a-job" / "contracts" / "schemas" / "discover.schema.json"
    )
    discover_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=payload, schema=discover_schema)
    assert payload["items"] == []
    assert err == ""
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules


def test_apply_human_mode_success(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    events = [
        {"event": "start", "profile": "dev"},
        {"event": "item", "id": "item-1", "status": "in_progress"},
        {"event": "submitted", "id": "item-1", "confirmation_text": "OK"},
        {"event": "end", "summary": {"submitted": 1, "failed": 0}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, str]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: Any, mode: str):
        yield from events

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(orchestrator_module, "iter_apply_events", fake_iter_apply_events)

    code, out, err = _run_cli(orchestrator_module, ["apply", "--profile", "dev"], monkeypatch)

    assert code == 0
    assert "Started apply session" in out
    assert err == ""
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules


def test_resume_job_json_contract(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    def fake_resume(job_id: str) -> dict[str, Any]:
        return {"id": job_id, "status": "in_progress", "resumed_from_step": 2}

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.resume_job", fake_resume)

    code, out, err = _run_cli(
        orchestrator_module, ["resume-job", "abc123", "--json"], monkeypatch
    )

    assert code == 0
    payload = json.loads(out)
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo / "specs" / "001-as-a-job" / "contracts" / "schemas" / "resume-job.schema.json"
    )
    resume_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=payload, schema=resume_schema)
    assert payload["id"] == "abc123"
    assert payload["status"] == "in_progress"
    assert err == ""


def test_apply_json_event_schema(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    events = [
        {"event": "start", "profile": "dev"},
        {"event": "item", "id": "item-1", "status": "in_progress"},
        {
            "event": "submitted",
            "id": "item-1",
            "confirmation_text": "Submitted",
            "confirmation_id": "CONF-42",
        },
        {"event": "end", "summary": {"submitted": 1, "failed": 0}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, str]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: Any, mode: str):
        yield from events

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(orchestrator_module, "iter_apply_events", fake_iter_apply_events)

    code, out, err = _run_cli(
        orchestrator_module, ["apply", "--profile", "dev", "--json"], monkeypatch
    )

    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo / "specs" / "001-as-a-job" / "contracts" / "schemas" / "apply-event.schema.json"
    )
    event_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for ln in lines:
        evt = json.loads(ln)
        validate(instance=evt, schema=event_schema)
    assert err == ""
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules
