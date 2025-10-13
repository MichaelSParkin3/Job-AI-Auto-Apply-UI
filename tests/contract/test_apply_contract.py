"""Contract tests for the `apply` CLI command."""

from __future__ import annotations

import contextlib
import importlib
import json
import os
import sys
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate

from job_ai_auto_apply_ui.application_queue import (
    ApplicationItem,
    ApplicationStatus,
    Artifacts,
    Reason,
)
from job_ai_auto_apply_ui.profile_manager import Profile


def _load_orchestrator() -> Any:
    """Import orchestrator while keeping browser modules unloaded."""

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
    """Yield a fresh orchestrator module for each test."""

    return _load_orchestrator()


def _run_cli(module: Any, args: Iterable[str]) -> tuple[int, str, str]:
    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = module.main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.fixture()
def apply_schema() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = (
        repo_root / "specs" / "001-as-a-job" / "contracts" / "schemas" / "apply-event.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTO_APPLY_USE_LLM_LOCATOR", raising=False)
    monkeypatch.delenv("AUTO_APPLY_DEBUG_RESUME_WIDGET", raising=False)
    monkeypatch.delenv("AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS", raising=False)


def test_apply_json_stream_success(
    monkeypatch: pytest.MonkeyPatch,
    apply_schema: dict[str, Any],
    orchestrator_module: Any,
) -> None:
    """Streaming JSON events should match schema and exit code should be zero on success."""

    events: list[dict[str, Any]] = [
        {"event": "start", "profile": "front_end"},
        {"event": "item", "id": "item-1", "status": "in_progress"},
        {
            "event": "submitted",
            "id": "item-1",
            "confirmation_id": "CONF-123",
            "confirmation_text": "Submitted",
        },
        {"event": "end", "summary": {"submitted": 1, "failed": 0}},
    ]

    def fake_load_profile(profile_id: str) -> dict[str, Any]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: dict[str, Any], mode: str) -> Iterator[dict[str, Any]]:
        assert mode == "supervised"
        yield from events

    monkeypatch.setattr("job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile)
    monkeypatch.setattr(orchestrator_module, "iter_apply_events", fake_iter_apply_events)

    code, out, err = _run_cli(orchestrator_module, ["apply", "--profile", "front_end", "--json"])

    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == len(events)
    for raw in lines:
        payload = json.loads(raw)
        validate(instance=payload, schema=apply_schema)
        if payload["event"] == "submitted":
            assert payload["confirmation_id"] == "CONF-123"
            assert payload.get("confirmation_text") == "Submitted"
    assert err == ""
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules


def test_apply_cli_accepts_extended_flags(
    monkeypatch: pytest.MonkeyPatch,
    orchestrator_module: Any,
) -> None:
    """The apply CLI should accept the documented override and diagnostics flags."""

    captured: dict[str, Any] = {}

    def fake_load_profile(profile_id: str) -> dict[str, Any]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: Any, mode: str) -> Iterator[dict[str, Any]]:
        captured["profile"] = profile
        captured["mode"] = mode
        profile_id = profile.id if hasattr(profile, "id") else profile["id"]
        yield {"event": "start", "profile": profile_id}
        yield {"event": "end", "summary": {"submitted": 0, "failed": 0}}

    monkeypatch.setattr("job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile)
    monkeypatch.setattr(orchestrator_module, "iter_apply_events", fake_iter_apply_events)

    code, out, err = _run_cli(
        orchestrator_module,
        [
            "apply",
            "--profile",
            "front_end",
            "--json",
            "--llm-provider",
            "openrouter",
            "--llm-model",
            "gpt-best",
            "--use-llm-locator",
            "--debug-resume-widget",
            "--resume-wait-timeout-seconds",
            "45",
        ],
    )

    assert code == 0
    assert err == ""
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules
    assert captured["mode"] == "supervised"
    profile_obj = captured["profile"]
    profile_id = profile_obj.id if hasattr(profile_obj, "id") else profile_obj["id"]
    assert profile_id == "front_end"
    assert os.environ["AUTO_APPLY_USE_LLM_LOCATOR"] == "1"
    assert os.environ["AUTO_APPLY_DEBUG_RESUME_WIDGET"] == "1"
    assert os.environ["AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS"] == "45"


def test_apply_stream_handles_failure(
    monkeypatch: pytest.MonkeyPatch,
    apply_schema: dict[str, Any],
    orchestrator_module: Any,
) -> None:
    """Failure events should surface in JSON stream with proper exit code."""

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

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile",
        lambda profile_id: {"id": profile_id},
    )
    monkeypatch.setattr(
        orchestrator_module,
        "iter_apply_events",
        lambda profile, mode: iter(events),
    )

    code, out, err = _run_cli(
        orchestrator_module,
        ["apply", "--profile", "front_end", "--json", "--auto"],
    )

    assert code == 3
    for raw in (ln for ln in out.splitlines() if ln.strip()):
        payload = json.loads(raw)
        validate(instance=payload, schema=apply_schema)
    assert err == ""
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules


def test_iter_apply_events_attaches_confirmation_id(
    monkeypatch: pytest.MonkeyPatch,
    orchestrator_module: Any,
) -> None:
    """Submitted events should include confirmation_id when artifacts provide it."""

    queue_items: list[ApplicationItem] = []

    class _QueueStub:
        def __init__(self, profile_id: str, base_dir: Path | None = None) -> None:
            self.profile_id = profile_id
            self._items = queue_items

        def pending(self) -> list[ApplicationItem]:
            return list(self._items)

        def resume(self, item_id: str) -> None:
            for itm in self._items:
                if itm.id == item_id:
                    itm.status = ApplicationStatus.IN_PROGRESS

        def mark_submitted(self, item_id: str, artifacts: Artifacts) -> None:
            return None

        def mark_failed(self, item_id: str, reason: object) -> None:
            raise AssertionError("Should not mark failed in this test")

        def update(self, item: ApplicationItem) -> None:
            return None

    class _TimelineStub:
        def info(self, *args: object, **kwargs: object) -> None:
            return None

        def warning(self, *args: object, **kwargs: object) -> None:
            return None

    class _OptionsStub:
        def apply_stealth_environment(self) -> None:
            return None

        def to_browser_use_kwargs(self) -> dict[str, object]:
            return {}

        @classmethod
        def from_settings(cls, profile: Profile) -> "_OptionsStub":  # pragma: no cover
            return cls()

    class _SessionStub:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def start(self) -> None:
            return None

        async def stop(self) -> None:
            return None

    class _AgentStub:
        def __init__(self, options: object) -> None:
            self.options = options

        async def execute_in_browser(
            self,
            session: object,
            profile: Profile,
            item: ApplicationItem,
            mode: str,
        ) -> Artifacts | Reason:
            if item.id == "with-confirm":
                return Artifacts(confirmation_text="OK", confirmation_id="CONF-789")
            return Artifacts(confirmation_text="OK", confirmation_id=None)

    now = datetime.now(UTC)
    queue_items[:] = [
        ApplicationItem(
            id="with-confirm",
            url="https://jobs.example.com/role-1",
            company="Example",
            title="Engineer",
            status=ApplicationStatus.NEW,
            discovered_at=now,
            last_updated_at=now,
            hash="hash-1",
            artifacts=Artifacts(),
            details=None,
            reason=None,
        ),
        ApplicationItem(
            id="without-confirm",
            url="https://jobs.example.com/role-2",
            company="Example",
            title="Engineer",
            status=ApplicationStatus.NEW,
            discovered_at=now,
            last_updated_at=now,
            hash="hash-2",
            artifacts=Artifacts(),
            details=None,
            reason=None,
        ),
    ]

    monkeypatch.setattr(
        orchestrator_module,
        "ApplicationQueue",
        _QueueStub,
    )
    monkeypatch.setattr(
        orchestrator_module,
        "bind_timeline",
        lambda *args, **kwargs: _TimelineStub(),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "log_event",
        lambda *args, **kwargs: None,
    )

    def _runtime_loader() -> tuple[type[Any], type[Any], type[Any]]:
        return _OptionsStub, _AgentStub, _SessionStub

    monkeypatch.setattr(orchestrator_module, "_load_browser_runtime", _runtime_loader)

    profile = Profile(
        id="front_end",
        name="Front End",
        resume_path=Path("resume.pdf"),
        defaults={},
        keywords={},
        prompts={},
        user_data_dir=None,
        preferred_browser=None,
    )

    events = list(orchestrator_module.iter_apply_events(profile, "supervised"))

    submitted_events = [event for event in events if event["event"] == "submitted"]
    assert {event["id"] for event in submitted_events} == {"with-confirm", "without-confirm"}

    for event in submitted_events:
        if event["id"] == "with-confirm":
            assert event["confirmation_id"] == "CONF-789"
        else:
            assert "confirmation_id" not in event


def test_apply_json_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
    apply_schema: dict[str, Any],
    orchestrator_module: Any,
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

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile",
        lambda profile_id: {"id": profile_id},
    )
    monkeypatch.setattr(
        orchestrator_module,
        "iter_apply_events",
        lambda profile, mode: iter(events),
    )

    code, out, err = _run_cli(
        orchestrator_module,
        ["apply", "--profile", "front_end", "--json", "--auto"],
    )

    assert code == 3
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) == len(events)
    for raw in lines:
        payload = json.loads(raw)
        validate(instance=payload, schema=apply_schema)
    assert err == ""
    assert "job_ai_auto_apply_ui.browser_agent.lever" not in sys.modules
