from __future__ import annotations

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from job_ai_auto_apply_ui.browser_agent.lever import LeverApplyAgent

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.asyncio
async def test_build_plan_in_browser_exposes_step1_schema() -> None:
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

    assert isinstance(plan, dict), "build_plan_in_browser should return JSON-serialisable plan"
    assert set(plan) >= {"meta", "widgets", "fields", "submit"}

    meta = plan["meta"]
    assert meta["formRoot"] == "form#application-form, #application"
    assert meta["captchaSelector"] == ".h-captcha, .g-recaptcha"
    assert meta["requiresLocationGate"] is True
    assert meta["eeoRoot"] == ".eeo-survey, #eeo-survey"

    resume_widget = plan["widgets"]["resume"]
    assert resume_widget["input"]["primary"] == "#resume-upload-input"
    assert resume_widget["input"]["alternates"][0] == "[data-qa='input-resume']"
    assert set(resume_widget["successSignals"]) >= {
        ".resume-upload-success",
        ".application-upload-success",
    }
    assert ".resume-upload-failure" in resume_widget["failureSignals"]

    fields_by_name = {field["name"]: field for field in plan["fields"]}
    assert {"name", "email", "phone", "location"} <= set(fields_by_name)

    email_field = fields_by_name["email"]
    assert email_field["pattern"] == "[a-zA-Z0-9.#$%&'*+\\/=?^_`{|}~-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
    assert email_field["selectorMeta"]["primary"] == "input[name='email'][data-qa='email-input']"

    location_field = fields_by_name["location"]
    assert location_field["selectorMeta"]["primary"] == "#location-input"
    assert "[data-qa='location-input']" in location_field["selectorMeta"]["alternates"]
    assert (
        location_field["aux"]["selectedLocationHidden"]
        == "input#selected-location[name='selectedLocation']"
    )

    submit = plan["submit"]
    assert submit["selector"]["primary"] == "button#btn-submit"
    assert "button[type='submit']" in submit["selector"]["alternates"]
