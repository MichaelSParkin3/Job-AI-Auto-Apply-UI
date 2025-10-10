"""Contract tests for saved-state CLI commands: review-mode, resume, replay, cleanup."""

from __future__ import annotations

import contextlib
import importlib
import json
import sys
from io import StringIO
from typing import Any, Iterable

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


def _run_cli(
    module: Any, args: Iterable[str], monkeypatch: pytest.MonkeyPatch
) -> tuple[int, str, str]:
    """Execute CLI entrypoint with environment isolation and captured stdio."""
    monkeypatch.setenv("AUTO_APPLY_BROWSER_MODE", "off")
    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


def test_apply_review_mode_flag_parses(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test that --review-mode flag is accepted by apply command."""
    events = [
        {"event": "start", "profile": "test"},
        {
            "event": "saved_for_review",
            "id": "01HXYZ",
            "form_state_path": "data/artifacts/test/01HXYZ/pre.json",
            "screenshot_before_path": "data/artifacts/test/01HXYZ/pre-full.jpg",
        },
        {"event": "end", "summary": {"submitted": 0, "failed": 0}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, str]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: Any, mode: str):
        yield from events

    monkeypatch.setattr("job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile)
    monkeypatch.setattr(orchestrator_module, "iter_apply_events", fake_iter_apply_events)

    code, out, err = _run_cli(
        orchestrator_module, ["apply", "--profile", "test", "--review-mode", "--json"], monkeypatch
    )

    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == 3

    # Verify saved_for_review event structure
    saved_event = json.loads(lines[1])
    assert saved_event["event"] == "saved_for_review"
    assert "form_state_path" in saved_event
    assert "screenshot_before_path" in saved_event


def test_apply_audit_after_submit_flags_parse(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test that --audit-after-submit and --no-audit-after-submit flags are accepted."""
    events = [
        {"event": "start", "profile": "test"},
        {
            "event": "submitted",
            "id": "01HXYZ",
            "confirmation_text": "Thank you",
            "confirmation_id": "CONF-123",
            "screenshot_after_path": "data/artifacts/test/01HXYZ/post-full.jpg",
        },
        {"event": "end", "summary": {"submitted": 1, "failed": 0}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, str]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: Any, mode: str):
        yield from events

    monkeypatch.setattr("job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile)
    monkeypatch.setattr(orchestrator_module, "iter_apply_events", fake_iter_apply_events)

    # Test --audit-after-submit
    code1, out1, _ = _run_cli(
        orchestrator_module,
        ["apply", "--profile", "test", "--audit-after-submit", "--json"],
        monkeypatch,
    )
    assert code1 == 0

    # Test --no-audit-after-submit
    code2, out2, _ = _run_cli(
        orchestrator_module,
        ["apply", "--profile", "test", "--no-audit-after-submit", "--json"],
        monkeypatch,
    )
    assert code2 == 0


def test_resume_job_with_submit_flag(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test resume-job accepts --submit flag and returns correct structure."""

    def fake_resume(job_id: str, submit: bool = False) -> dict[str, Any]:
        if submit:
            return {
                "id": job_id,
                "status": "submitted",
                "confirmation_text": "Application submitted",
            }
        return {"id": job_id, "status": "paused", "message": "Review and press enter to submit"}

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.resume_job", fake_resume)

    # Test without --submit
    code1, out1, _ = _run_cli(orchestrator_module, ["resume-job", "01HXYZ", "--json"], monkeypatch)
    assert code1 == 0
    payload1 = json.loads(out1)
    assert payload1["id"] == "01HXYZ"
    assert payload1["status"] == "paused"

    # Test with --submit
    code2, out2, _ = _run_cli(
        orchestrator_module, ["resume-job", "01HXYZ", "--submit", "--json"], monkeypatch
    )
    assert code2 == 0
    payload2 = json.loads(out2)
    assert payload2["id"] == "01HXYZ"
    assert payload2["status"] == "submitted"


def test_replay_job_command_exists(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test replay-job command parses and returns correct exit code."""

    def fake_replay(job_id: str) -> dict[str, Any]:
        return {"id": job_id, "status": "in_progress"}

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.replay_job", fake_replay)

    code, out, _ = _run_cli(orchestrator_module, ["replay-job", "01HXYZ", "--json"], monkeypatch)

    assert code == 0
    payload = json.loads(out)
    assert payload["id"] == "01HXYZ"
    assert payload["status"] == "in_progress"


def test_cleanup_artifacts_requires_older_than(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test cleanup-artifacts requires --older-than flag and rejects missing arg."""

    def fake_cleanup(profile: str | None, older_than: int, dry_run: bool) -> dict[str, Any]:
        return {"matched": 5, "deleted": 0 if dry_run else 5}

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.cleanup_artifacts", fake_cleanup)

    # Test missing --older-than returns exit code 5
    code1, out1, err1 = _run_cli(orchestrator_module, ["cleanup-artifacts", "--json"], monkeypatch)
    assert code1 == 5  # invalid args

    # Test with --older-than succeeds
    code2, out2, _ = _run_cli(
        orchestrator_module, ["cleanup-artifacts", "--older-than", "30", "--json"], monkeypatch
    )
    assert code2 == 0
    payload = json.loads(out2)
    assert "matched" in payload or "deleted" in payload


def test_cleanup_artifacts_dry_run_flag(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test cleanup-artifacts --dry-run flag works correctly."""

    def fake_cleanup(profile: str | None, older_than: int, dry_run: bool) -> dict[str, Any]:
        files = [
            "data/artifacts/profile1/item1/pre.json",
            "data/artifacts/profile1/item1/pre-full.jpg",
        ]
        deleted_count = 0 if dry_run else len(files)
        return {
            "matched": len(files),
            "files": files if dry_run else [],
            "deleted": deleted_count,
        }

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.cleanup_artifacts", fake_cleanup)

    code, out, _ = _run_cli(
        orchestrator_module,
        ["cleanup-artifacts", "--older-than", "30", "--dry-run", "--json"],
        monkeypatch,
    )

    assert code == 0
    payload = json.loads(out)
    assert payload["matched"] == 2
    assert "files" in payload


def test_captcha_blocked_event_includes_artifacts(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test captcha_blocked event includes form_state_path and screenshot_before_path."""
    events = [
        {"event": "start", "profile": "test"},
        {
            "event": "captcha_blocked",
            "id": "01HXYZ",
            "form_state_path": "data/artifacts/test/01HXYZ/pre.json",
            "screenshot_before_path": "data/artifacts/test/01HXYZ/pre-full.jpg",
        },
        {"event": "end", "summary": {"submitted": 0, "failed": 0}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, str]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: Any, mode: str):
        yield from events

    monkeypatch.setattr("job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile)
    monkeypatch.setattr(orchestrator_module, "iter_apply_events", fake_iter_apply_events)

    code, out, _ = _run_cli(
        orchestrator_module, ["apply", "--profile", "test", "--json"], monkeypatch
    )

    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    captcha_event = json.loads(lines[1])
    assert captcha_event["event"] == "captcha_blocked"
    assert "form_state_path" in captcha_event
    assert "screenshot_before_path" in captcha_event


def test_resume_job_invalid_state_exit_code(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test resume-job returns exit code 6 when saved state is missing/corrupt."""

    def fake_resume(job_id: str, submit: bool = False) -> dict[str, Any]:
        # Simulate missing pre.json
        raise ValueError("pre.json missing or invalid")

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.resume_job", fake_resume)

    code, out, _ = _run_cli(orchestrator_module, ["resume-job", "01HXYZ", "--json"], monkeypatch)

    assert code == 6  # invalid_state exit code
    payload = json.loads(out)
    assert payload["id"] == "01HXYZ"
    assert payload["status"] == "invalid_state"
    assert "error" in payload


def test_cleanup_artifacts_nothing_matched_exit_code(
    monkeypatch: pytest.MonkeyPatch, orchestrator_module: Any
) -> None:
    """Test cleanup-artifacts returns exit code 2 when nothing matched."""

    def fake_cleanup(profile: str | None, older_than: int, dry_run: bool) -> dict[str, Any]:
        return {"matched": 0, "deleted": 0}

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.cleanup_artifacts", fake_cleanup)

    code, out, _ = _run_cli(
        orchestrator_module, ["cleanup-artifacts", "--older-than", "999", "--json"], monkeypatch
    )

    assert code == 2  # nothing matched
