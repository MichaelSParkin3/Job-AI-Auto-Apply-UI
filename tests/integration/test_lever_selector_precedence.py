from __future__ import annotations

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from job_ai_auto_apply_ui.browser_agent.lever import LeverApplyAgent

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.asyncio
async def test_selector_precedence_captures_alternates() -> None:
    html = (FIXTURES / "lever_step1_form.html").read_text(encoding="utf-8")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(html)

            agent = LeverApplyAgent()
            plan = await agent.build_plan_in_browser(page)
        finally:
            await browser.close()

    resume_input = plan["widgets"]["resume"]["input"]
    assert resume_input["precedence"] == ["id", "data-qa", "name", "role", "text", "nth"]
    assert resume_input["alternates"] == [
        "[data-qa='input-resume']",
        "input[type='file'][name='resume']",
    ]

    fields_by_name = {field["name"]: field for field in plan["fields"]}

    name_meta = fields_by_name["name"]["selectorMeta"]
    assert name_meta["precedence"] == ["name", "id", "data-qa", "aria", "text", "nth"]
    assert name_meta["primary"] == "input[name='name'][data-qa='name-input']"
    assert name_meta["alternates"] == [
        "#candidate-name",
        "input[data-qa='name-input']",
    ]

    long_form = fields_by_name["additionalQuestions[0][field0]"]
    textarea_meta = long_form["selectorMeta"]
    assert textarea_meta["primary"] == "textarea[name='additionalQuestions[0][field0]']"
    assert textarea_meta["precedence"][0] == "name"
    assert "textarea#additional-question-0" in textarea_meta["alternates"]
