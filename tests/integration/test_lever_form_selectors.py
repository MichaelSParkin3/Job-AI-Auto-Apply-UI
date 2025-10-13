from pathlib import Path

import pytest

from job_ai_auto_apply_ui.browser_agent.lever import (
    LeverApplyAgent,
    LeverBrowserOptions,
    ensure_allowed_domain,
)
from job_ai_auto_apply_ui.profile_manager import Profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _profile() -> Profile:
    return Profile(
        id="front_end",
        name="Front End",
        resume_path=Path("resume.pdf"),
        defaults={},
        keywords={"roles": ["Senior Front End Developer"]},
        prompts={},
    )


def test_form_plan_and_allowed_domains(monkeypatch: pytest.MonkeyPatch) -> None:
    html = (FIXTURES / "lever_form.html").read_text(encoding="utf-8")
    monkeypatch.setenv("ALLOWED_DOMAINS", "jobs.lever.co,careers.example.com")
    monkeypatch.setenv("AUTO_APPLY_DIAGNOSTICS", "true")
    monkeypatch.setenv("AUTO_APPLY_CAPTURE_VIDEO", "0")
    options = LeverBrowserOptions.from_settings(profile=_profile())

    kwargs = options.to_browser_use_kwargs()
    assert kwargs["allowed_domains"] == ["jobs.lever.co", "careers.example.com"]

    agent = LeverApplyAgent(options=options)
    plan = agent.build_plan(html)

    assert plan.resume_input == "#resume-upload-input"
    assert "email" in plan.contact_fields
    assert plan.dynamic_questions

    ensure_allowed_domain("https://jobs.lever.co/example/123", options.allowed_domains)
    with pytest.raises(ValueError):
        ensure_allowed_domain("https://malicious.example/", options.allowed_domains)
