from __future__ import annotations

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from job_ai_auto_apply_ui.browser_agent import lever

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.asyncio
async def test_location_gate_requires_hidden_name(monkeypatch: pytest.MonkeyPatch) -> None:
    html = (FIXTURES / "lever_step1_form.html").read_text(encoding="utf-8")
    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(lever, "log_event", lambda name, **payload: events.append((name, payload)))

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(html)

            ok, state = await lever.validate_location_gate(
                page,
                input_selector="#location-input",
                hidden_selector="#selected-location",
            )
            assert ok is False
            assert state["name"] == ""
            assert any(name == "form.location_gate.missing" for name, _ in events)

            events.clear()
            await page.evaluate(
                "(hidden) => { const el = document.querySelector(hidden); el.value = '{\\"name\\": \\"San Francisco, CA\\"}'; el.dispatchEvent(new Event('change', { bubbles: true })); }",
                "#selected-location",
            )

            ok, state = await lever.validate_location_gate(
                page,
                input_selector="#location-input",
                hidden_selector="#selected-location",
            )
            assert ok is True
            assert state["name"] == "San Francisco, CA"
            assert any(name == "form.location_gate.ready" for name, _ in events)
        finally:
            await browser.close()
