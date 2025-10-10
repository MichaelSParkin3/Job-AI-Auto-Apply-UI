"""Contract test: resume-job invalid_state exit code 6 + JSON error."""

from __future__ import annotations

import contextlib
import importlib
import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any

import pytest


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


def _run_cli(module: Any, args: list[str], monkeypatch: pytest.MonkeyPatch) -> tuple[int, str, str]:
    """Execute CLI entrypoint with environment isolation and captured stdio."""
    monkeypatch.setenv("AUTO_APPLY_BROWSER_MODE", "off")
    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


def test_resume_job_missing_pre_json_exit_code_6(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test that resume-job returns exit code 6 when pre.json is missing."""

    # Setup temp directory with queue but no artifacts
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create queue with one item
        from job_ai_auto_apply_ui.application_queue import ApplicationItem

        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/missing-state",
            company="TestCorp",
            title="Missing State Job",
            details=None,
            source_query="test",
            source_rank=1,
        )
        item_id = item.id

        queue_data = {"items": [item.to_dict()]}
        queue_path = queue_dir / "test_profile.json"
        queue_path.write_text(json.dumps(queue_data), encoding="utf-8")

        # Mock cwd to use temp directory
        monkeypatch.setattr("pathlib.Path.cwd", lambda: base_dir)

        # Run resume-job without pre.json present
        code, out, _err = _run_cli(
            orchestrator_module, ["resume-job", item_id, "--json"], monkeypatch
        )

        # Assertions
        assert code == 6, f"Expected exit code 6, got {code}"

        payload = json.loads(out)
        assert payload["id"] == item_id
        assert payload["status"] == "invalid_state"
        assert "error" in payload
        assert "pre.json" in payload["error"].lower() or "missing" in payload["error"].lower()


def test_resume_job_corrupt_pre_json_exit_code_6(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test that resume-job returns exit code 6 when pre.json is corrupt."""

    # Setup temp directory with queue and corrupt pre.json
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create queue with one item
        from job_ai_auto_apply_ui.application_queue import ApplicationItem

        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/corrupt-state",
            company="TestCorp",
            title="Corrupt State Job",
            details=None,
            source_query="test",
            source_rank=1,
        )
        item_id = item.id

        queue_data = {"items": [item.to_dict()]}
        queue_path = queue_dir / "test_profile.json"
        queue_path.write_text(json.dumps(queue_data), encoding="utf-8")

        # Create corrupt pre.json
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.config.Settings.artifacts_root",
            str(base_dir / "artifacts"),
        )

        artifact_dir = base_dir / "artifacts" / "test_profile" / item_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        pre_json_path = artifact_dir / "pre.json"
        pre_json_path.write_text("{ invalid json content }", encoding="utf-8")

        # Mock cwd to use temp directory
        monkeypatch.setattr("pathlib.Path.cwd", lambda: base_dir)

        # Run resume-job with corrupt pre.json
        code, out, _err = _run_cli(
            orchestrator_module, ["resume-job", item_id, "--json"], monkeypatch
        )

        # Assertions
        assert code == 6, f"Expected exit code 6, got {code}"

        payload = json.loads(out)
        assert payload["id"] == item_id
        assert payload["status"] == "invalid_state"
        assert "error" in payload
        assert (
            "pre.json" in payload["error"].lower()
            or "invalid" in payload["error"].lower()
            or "corrupt" in payload["error"].lower()
        )


def test_resume_job_invalid_state_json_structure(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test that invalid_state error returns correct JSON structure."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create queue with one item
        from job_ai_auto_apply_ui.application_queue import ApplicationItem

        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/json-structure",
            company="TestCorp",
            title="JSON Structure Job",
            details=None,
            source_query="test",
            source_rank=1,
        )
        item_id = item.id

        queue_data = {"items": [item.to_dict()]}
        queue_path = queue_dir / "test_profile.json"
        queue_path.write_text(json.dumps(queue_data), encoding="utf-8")

        # Mock cwd to use temp directory
        monkeypatch.setattr("pathlib.Path.cwd", lambda: base_dir)

        # Run resume-job without pre.json
        code, out, _err = _run_cli(
            orchestrator_module, ["resume-job", item_id, "--json"], monkeypatch
        )

        # Parse JSON output
        payload = json.loads(out)

        # Verify required fields
        assert "id" in payload, "JSON must contain 'id' field"
        assert "status" in payload, "JSON must contain 'status' field"
        assert "error" in payload, "JSON must contain 'error' field"

        assert payload["id"] == item_id
        assert payload["status"] == "invalid_state"
        assert isinstance(payload["error"], str)
        assert len(payload["error"]) > 0


def test_resume_job_not_found_vs_invalid_state(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test that not_found (exit 4) is different from invalid_state (exit 6)."""

    # Setup temp directory with empty queue
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create empty queue
        queue_path = queue_dir / "test_profile.json"
        queue_path.write_text(json.dumps({"items": []}), encoding="utf-8")

        # Mock cwd to use temp directory
        monkeypatch.setattr("pathlib.Path.cwd", lambda: base_dir)

        # Run resume-job with non-existent id
        code, out, _err = _run_cli(
            orchestrator_module, ["resume-job", "nonexistent-id", "--json"], monkeypatch
        )

        # Should be exit code 4 (not found), not 6 (invalid_state)
        assert code == 4, f"Expected exit code 4 for not_found, got {code}"

        payload = json.loads(out)
        assert payload["status"] == "not_found"
