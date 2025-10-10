"""Contract tests for the `resume-job` CLI command."""

from __future__ import annotations

import contextlib
import importlib
import json
import sys
from collections.abc import Iterable
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate


def _load_orchestrator() -> Any:
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


def _run_cli(module: Any, args: Iterable[str]) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.fixture()
def resume_schema() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = (
        repo_root / "specs" / "001-as-a-job" / "contracts" / "schemas" / "resume-job.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_resume_success(
    monkeypatch: pytest.MonkeyPatch, resume_schema: dict[str, Any], orchestrator_module: Any
) -> None:
    """Successful resume returns JSON payload and exit code zero."""

    def fake_resume(job_id: str) -> dict[str, Any]:
        return {"id": job_id, "status": "in_progress", "resumed_from_step": 2}

    monkeypatch.setattr(orchestrator_module, "resume_job", fake_resume)

    code, out, err = _run_cli(orchestrator_module, ["resume-job", "app-123", "--json"])

    assert code == 0
    payload = json.loads(out)
    validate(instance=payload, schema=resume_schema)
    assert payload["id"] == "app-123"
    assert payload["status"] == "in_progress"
    assert err == ""


def test_resume_not_found(
    monkeypatch: pytest.MonkeyPatch, resume_schema: dict[str, Any], orchestrator_module: Any
) -> None:
    """Resume should exit with code 4 when the job cannot be located."""

    def fake_resume(job_id: str) -> dict[str, Any]:
        raise LookupError(job_id)

    monkeypatch.setattr(orchestrator_module, "resume_job", fake_resume)

    code, out, err = _run_cli(orchestrator_module, ["resume-job", "missing", "--json"])

    assert code == 4
    payload = json.loads(out)
    validate(instance=payload, schema=resume_schema)
    assert payload["id"] == "missing"
    assert payload["status"] == "not_found"
    assert err == ""
