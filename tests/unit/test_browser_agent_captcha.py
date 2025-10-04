from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from job_ai_auto_apply_ui.application_queue import Reason
from job_ai_auto_apply_ui.browser_agent import lever


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

    reason = await lever.handle_captcha_block(
        page,
        state=state,
        capture_callback=fake_capture_artifacts,
    )

    assert isinstance(reason, Reason)
    assert reason.code == "captcha_blocked"
    assert captured, "artifacts should be captured before returning"
    assert any(name == "captcha.blocking_visible" for name, _ in events)
