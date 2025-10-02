from pathlib import Path

from job_ai_auto_apply_ui.application_queue import JobDetails
from job_ai_auto_apply_ui.llm.prompt_builder import PromptBuilder, Question
from job_ai_auto_apply_ui.profile_manager import Profile


def _profile() -> Profile:
    return Profile(
        id="front_end",
        name="Front End",
        resume_path=Path("resume.pdf"),
        defaults={"summary": "Seasoned FE engineer"},
        keywords={"roles": ["React", "TypeScript"]},
        prompts={"portfolio": "Reference UI system work."},
    )


def _job() -> JobDetails:
    return JobDetails(
        location="Remote",
        work_model="remote",
        employment_type="full_time",
        posting_excerpt="Join our distributed team to build polished experiences.",
    )


def test_cached_answer_short_circuits_llm() -> None:
    builder = PromptBuilder(_profile(), cache={"why react": "Because it's fast"})
    question = Question(id="q1", text="Why React?", required=False)

    plan = builder.build_question_prompt(question=question, job=_job())

    assert plan.cache_key == "why react"
    assert plan.messages[-1]["content"] == "Because it's fast"


def test_prompt_includes_required_hint() -> None:
    builder = PromptBuilder(_profile(), provider="openrouter")
    question = Question(id="q2", text="Describe your UI leadership", required=True)

    plan = builder.build_question_prompt(question=question, job=_job())

    system = plan.messages[0]["content"]
    user = plan.messages[1]["content"]
    assert "openrouter" in system.lower()
    assert "This question is required" in user


def test_prompt_appends_extra_context() -> None:
    builder = PromptBuilder(_profile())
    question = Question(id="q3", text="Portfolio highlights", required=False)

    plan = builder.build_question_prompt(
        question=question,
        job=_job(),
        extra_context=["Emphasize accessibility wins."],
    )

    assert "Emphasize accessibility wins." in plan.messages[1]["content"]
