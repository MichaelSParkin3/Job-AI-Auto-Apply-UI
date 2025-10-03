"""Contract tests for the `apply` CLI command."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
import os
import sys
import types
import json
from collections.abc import Iterable, Iterator
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate

if "job_ai_auto_apply_ui.browser_agent" not in sys.modules:
    browser_agent_stub = types.ModuleType("job_ai_auto_apply_ui.browser_agent")

    class _StubLeverApplyAgent:  # pragma: no cover - test helper
        pass

    browser_agent_stub.LeverApplyAgent = _StubLeverApplyAgent

    class _StubLeverBrowserOptions:  # pragma: no cover - test helper
        @classmethod
        def from_settings(cls, profile: object) -> "_StubLeverBrowserOptions":
            return cls()

        def apply_stealth_environment(self) -> None:
            return None

        def to_browser_use_kwargs(self) -> dict[str, object]:
            return {}

    browser_agent_stub.LeverBrowserOptions = _StubLeverBrowserOptions
    browser_agent_stub.LeverFormPlan = object

    def _ensure_allowed_domain(url: str) -> None:
        return None

    browser_agent_stub.ensure_allowed_domain = _ensure_allowed_domain
    sys.modules["job_ai_auto_apply_ui.browser_agent"] = browser_agent_stub
    sys.modules["job_ai_auto_apply_ui.browser_agent.lever"] = browser_agent_stub

from job_ai_auto_apply_ui.application_queue import ApplicationItem, ApplicationStatus, Artifacts
from job_ai_auto_apply_ui.profile_manager import Profile
from job_ai_auto_apply_ui.orchestrator import iter_apply_events, main


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
        if payload["event"] == "submitted":
            assert payload["confirmation_id"] == "CONF-123"
            assert payload.get("confirmation_text") == "Submitted"
    assert err == ""


def test_apply_cli_accepts_extended_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """The apply CLI should accept the documented override and diagnostics flags."""

    captured: dict[str, Any] = {}
    monkeypatch.delenv("AUTO_APPLY_USE_LLM_LOCATOR", raising=False)
    monkeypatch.delenv("AUTO_APPLY_DEBUG_RESUME_WIDGET", raising=False)
    monkeypatch.delenv("AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS", raising=False)

    def fake_load_profile(profile_id: str) -> dict[str, Any]:
        return {"id": profile_id}

    def fake_iter_apply_events(profile: dict[str, Any], mode: str) -> Iterator[dict[str, Any]]:
        captured["profile"] = profile
        captured["mode"] = mode
        profile_id = profile.id if hasattr(profile, "id") else profile["id"]
        # Yield a minimal successful session
        yield {"event": "start", "profile": profile_id}
        yield {"event": "end", "summary": {"submitted": 0, "failed": 0}}

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.orchestrator.iter_apply_events", fake_iter_apply_events
    )

    code, _, err = _run_cli(
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
        ]
    )

    assert code == 0
    assert err == ""
    assert captured["mode"] == "supervised"
    # Environment variables should reflect the toggles for downstream helpers
    assert os.environ["AUTO_APPLY_USE_LLM_LOCATOR"] == "1"
    assert os.environ["AUTO_APPLY_DEBUG_RESUME_WIDGET"] == "1"
    assert os.environ["AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS"] == "45"


def test_iter_apply_events_includes_confirmation_id_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure the orchestrator surfaces confirmation identifiers when artifacts provide them."""

    now = datetime.now(UTC)
    item_with_id = ApplicationItem(
        id="with-confirm",
        url="https://jobs.example.com/1",
        company="ExampleCo",
        title="Engineer",
        status=ApplicationStatus.NEW,
        discovered_at=now,
        last_updated_at=now,
        hash="hash-confirm",
        artifacts=Artifacts(),
        details=None,
        reason=None,
    )
    item_without_id = ApplicationItem(
        id="without-confirm",
        url="https://jobs.example.com/2",
        company="ExampleCo",
        title="Engineer",
        status=ApplicationStatus.NEW,
        discovered_at=now,
        last_updated_at=now,
        hash="hash-no-confirm",
        artifacts=Artifacts(),
        details=None,
        reason=None,
    )

    class _QueueStub:
        def __init__(self, profile_id: str) -> None:
            self.profile_id = profile_id
            self._items = [item_with_id, item_without_id]

        def pending(self) -> list[ApplicationItem]:
            return list(self._items)

        def resume(self, item_id: str) -> None:
            for itm in self._items:
                if itm.id == item_id:
                    itm.status = ApplicationStatus.IN_PROGRESS

        def mark_submitted(self, item_id: str, artifacts: Artifacts) -> None:  # pragma: no cover - noop
            return None

        def mark_failed(self, item_id: str, reason: object) -> None:  # pragma: no cover - noop
            raise AssertionError("Should not mark failed in this test")

        def update(self, item: ApplicationItem) -> None:  # pragma: no cover - noop
            return None

    class _TimelineStub:
        def info(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - noop
            return None

        def warning(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - noop
            return None

    class _OptionsStub:
        def apply_stealth_environment(self) -> None:  # pragma: no cover - noop
            return None

        def to_browser_use_kwargs(self) -> dict[str, object]:  # pragma: no cover - noop
            return {}

    class _SessionStub:
        def __init__(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - noop
            return None

        async def start(self) -> None:  # pragma: no cover - noop
            return None

        async def stop(self) -> None:  # pragma: no cover - noop
            return None

    class _AgentStub:
        def __init__(self, options: object) -> None:  # pragma: no cover - noop
            self.options = options

        async def execute_in_browser(
            self,
            session: object,
            profile: Profile,
            item: ApplicationItem,
            mode: str,
        ) -> Artifacts:
            if item.id == "with-confirm":
                return Artifacts(confirmation_text="OK", confirmation_id="CONF-789")
            return Artifacts(confirmation_text="OK", confirmation_id=None)

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

    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.ApplicationQueue", _QueueStub)
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.orchestrator.bind_timeline", lambda *args, **kwargs: _TimelineStub()
    )
    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.log_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.orchestrator.LeverBrowserOptions.from_settings",
        classmethod(lambda cls, profile: _OptionsStub()),
    )
    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.LeverApplyAgent", _AgentStub)
    monkeypatch.setattr("job_ai_auto_apply_ui.orchestrator.BrowserSession", _SessionStub)

    events = list(iter_apply_events(profile, "supervised"))

    submitted_events = [event for event in events if event["event"] == "submitted"]
    assert {event["id"] for event in submitted_events} == {"with-confirm", "without-confirm"}

    for event in submitted_events:
        if event["id"] == "with-confirm":
            assert event["confirmation_id"] == "CONF-789"
        else:
            assert "confirmation_id" not in event



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
