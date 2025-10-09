from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from job_ai_auto_apply_ui.browser_agent import lever


@pytest.mark.asyncio
async def test_collect_invalid_field_selectors_reports_before_check(monkeypatch: pytest.MonkeyPatch) -> None:
    call_order: list[str] = []

    async def fake_evaluate(script: str, *_args, **_kwargs):
        call_order.append(script)
        if "reportValidity" in script:
            return None
        if "checkValidity" in script:
            return False
        if ":invalid" in script:
            return ["input[name='email']", "select#gender-select"]
        return None

    page = AsyncMock()
    page.evaluate.side_effect = fake_evaluate

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(lever, "log_event", lambda name, **payload: events.append((name, payload)))

    selectors = await lever.collect_invalid_field_selectors(page)

    assert selectors == ["input[name='email']", "select#gender-select"]
    assert any("reportValidity" in script for script in call_order)
    assert any("checkValidity" in script for script in call_order)
    report_index = next(i for i, script in enumerate(call_order) if "reportValidity" in script)
    check_index = next(i for i, script in enumerate(call_order) if "checkValidity" in script)
    assert report_index < check_index, "reportValidity should run before checkValidity"

    invalid_events = [payload for name, payload in events if name == "form.validation.invalid_fields"]
    assert invalid_events, "invalid selectors should be logged for observability"
    assert invalid_events[-1]["selectors"] == selectors
