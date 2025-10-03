from __future__ import annotations

from pathlib import Path

from job_ai_auto_apply_ui.browser_agent.lever import analyze_form


def test_analyze_form_extracts_selectors() -> None:
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    html = (fixtures / "lever_form.html").read_text(encoding="utf-8")

    plan = analyze_form(html)

    assert plan.resume_input == "#resume-upload-input"
    assert plan.contact_fields["email"].startswith("input")
    assert "urls[GitHub (If applicable)]" in plan.link_fields
    assert plan.dynamic_questions, "Expected at least one dynamic question"
    question = plan.dynamic_questions[0]
    assert question.prompt.lower().startswith("why")
    assert question.required is True
    assert question.answer_selector.startswith("textarea")
