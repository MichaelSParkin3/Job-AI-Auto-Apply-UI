from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from job_ai_auto_apply_ui.application_queue import (
    ApplicationItem,
    ApplicationStatus,
    Artifacts,
    JobDetails,
    Reason,
)
from job_ai_auto_apply_ui.browser_agent import lever
from job_ai_auto_apply_ui.profile_manager import Profile


def _minimal_profile(tmp_path: Path) -> Profile:
    resume = tmp_path / "resume.pdf"
    resume.write_text("resume", encoding="utf-8")
    return Profile(
        id="test",
        name="Test User",
        resume_path=resume,
        defaults={},
        keywords={},
        prompts={},
    )


def _queue_item(apply_url: str) -> ApplicationItem:
    now = datetime.now(UTC)
    return ApplicationItem(
        id="item-1",
        url=apply_url,
        company="Example",
        title="Engineer",
        status=ApplicationStatus.IN_PROGRESS,
        discovered_at=now,
        last_updated_at=now,
        hash="hash",
        artifacts=Artifacts(),
        details=JobDetails(apply_url=apply_url),
    )


@pytest.mark.asyncio
async def test_handle_captcha_block_requests_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state = {"present": True, "visible": True, "blocking": True, "cover": 0.42}
    page = AsyncMock()
    captured: list[str] = []

    async def fake_capture_artifacts(page_obj, *, prefix: str) -> dict[str, str]:
        assert page_obj is page
        captured.append(prefix)
        snapshot = tmp_path / f"{prefix}.html"
        snapshot.write_text("<html></html>", encoding="utf-8")
        return {"dom": str(snapshot)}

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(lever, "log_event", lambda name, **payload: events.append((name, payload)))

    reason = await lever.handle_captcha_block(page, state=state, capture_callback=fake_capture_artifacts)

    assert isinstance(reason, Reason)
    assert reason.code == "captcha_blocked"
    assert captured, "artifacts should be captured before returning"
    assert any(name == "captcha.blocking_visible" for name, _ in events)
    assert any(name == "captcha.blocking_captured" for name, _ in events)


@pytest.mark.asyncio
async def test_capture_review_artifacts_writes_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    options = lever.LeverBrowserOptions(
        allowed_domains=("jobs.lever.co",),
        capture_video=False,
        capture_har=False,
        artifacts_dir=tmp_path,
        locale="en-US",
        timezone="UTC",
        viewport_width=1280,
        viewport_height=720,
        disable_default_extensions=True,
    )
    agent = lever.LeverApplyAgent(options=options)

    class DummyPage:
        async def content(self) -> str:
            return "<html></html>"

        async def screenshot(self, path: str) -> None:
            Path(path).write_bytes(b"png")

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(lever, "log_event", lambda name, **payload: events.append((name, payload)))

    results = await agent._capture_review_artifacts(DummyPage(), prefix="captcha-block")

    assert "dom_snapshot_path" in results
    assert "screenshot_path" in results
    assert Path(results["dom_snapshot_path"]).exists()
    assert Path(results["screenshot_path"]).exists()
    assert any(name == "captcha.capture.artifacts" for name, _ in events)


@pytest.mark.asyncio
async def test_execute_in_browser_blocks_when_captcha_visible(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile = _minimal_profile(tmp_path)
    item = _queue_item("https://jobs.lever.co/example/apply")

    options = lever.LeverBrowserOptions(
        allowed_domains=("jobs.lever.co",),
        capture_video=False,
        capture_har=False,
        artifacts_dir=tmp_path,
        locale="en-US",
        timezone="UTC",
        viewport_width=1280,
        viewport_height=720,
        disable_default_extensions=True,
    )
    agent = lever.LeverApplyAgent(options=options)

    class DummyPage:
        async def content(self) -> str:
            return "<html></html>"

        async def screenshot(self, path: str) -> None:
            Path(path).write_bytes(b"png")

    class DummySession:
        def __init__(self, page_obj) -> None:
            self._page = page_obj

        async def new_page(self):
            return self._page

        async def get_current_page(self):
            return self._page

    dummy_page = DummyPage()
    session = DummySession(dummy_page)

    monkeypatch.setattr(lever, "_robust_navigate", AsyncMock())
    monkeypatch.setattr(lever, "_wait_for_any", AsyncMock())
    monkeypatch.setattr(agent, "build_plan_in_browser", AsyncMock(return_value={
        "meta": {"requiresLocationGate": False},
        "widgets": {"resume": {"input": {}}},
        "fields": [],
        "submit": {"selector": {"primary": "#submit"}},
    }))
    monkeypatch.setattr(lever, "_coerce_step1_plan", lambda raw: raw)
    monkeypatch.setattr(lever, "_plan_field_maps", lambda _: ({}, {}, []))
    monkeypatch.setattr(lever, "_set_structured_location", AsyncMock())
    monkeypatch.setattr(lever, "_upload_resume", AsyncMock(return_value=True))
    monkeypatch.setattr(lever, "_fill_if_available", AsyncMock())
    monkeypatch.setattr(lever, "_set_pronouns", AsyncMock())
    monkeypatch.setattr(lever, "collect_invalid_field_selectors", AsyncMock(return_value=[]))
    monkeypatch.setattr(lever, "_form_check_validity", AsyncMock(return_value=True))
    monkeypatch.setattr(lever, "_apply_llm_assist", AsyncMock())
    monkeypatch.setattr(lever, "_fill_textarea", AsyncMock())
    monkeypatch.setattr(lever, "_wait_for_resume_upload", AsyncMock(return_value=True))
    monkeypatch.setattr(lever, "_click", AsyncMock())
    monkeypatch.setattr(lever, "OpenRouterClient", AsyncMock())
    monkeypatch.setattr(lever, "OpenRouterError", Exception)
    monkeypatch.setattr(lever, "_extract_confirmation_text", AsyncMock(return_value="submitted"))
    monkeypatch.setattr(lever, "_hcaptcha_state", AsyncMock(return_value={"blocking": True, "visible": True}))

    captured_callbacks: list[object] = []

    original_handle = lever.handle_captcha_block

    async def capture_handle(page, *, state, capture_callback=None):
        captured_callbacks.append(capture_callback)
        return await original_handle(page, state=state, capture_callback=capture_callback)

    monkeypatch.setattr(lever, "handle_captcha_block", capture_handle)

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(lever, "log_event", lambda name, **payload: events.append((name, payload)))

    result = await agent.execute_in_browser(session=session, profile=profile, item=item, mode="auto")

    assert isinstance(result, Reason)
    assert result.code == "captcha_blocked"
    assert captured_callbacks and captured_callbacks[0] is not None
    dom_files = list(tmp_path.glob("captcha-block-*.html"))
    png_files = list(tmp_path.glob("captcha-block-*.png"))
    assert dom_files, "DOM artifact should be written"
    assert png_files, "Screenshot artifact should be written"
    assert any(name == "captcha.blocking_visible" for name, _ in events)
    assert any(name == "captcha.capture.artifacts" for name, _ in events)
