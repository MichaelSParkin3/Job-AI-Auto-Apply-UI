from pathlib import Path

from job_ai_auto_apply_ui.job_discovery import discover_jobs
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


def test_lever_details_extract_populates_job_details() -> None:
    profile = _profile()
    posting_html = (FIXTURES / "lever_posting.html").read_text(encoding="utf-8")
    search_html = """
    <html>
      <body>
        <div class="g">
          <a href="https://jobs.lever.co/example/123">Senior Frontend Engineer</a>
          <div class="VwiC3b">Work with a remote-first team delivering Lever automations.</div>
        </div>
      </body>
    </html>
    """

    items = discover_jobs(
        profile=profile,
        window_hours=24,
        cap=3,
        fetch_search=lambda _: search_html,
        fetch_posting=lambda _: posting_html,
    )

    assert len(items) == 1
    item = items[0]
    assert item.details is not None
    assert item.details.location == "Manila"
    assert item.details.apply_url.endswith("/apply")
    assert item.details.posting_excerpt
    assert item.details.source_rank == 1
    assert item.details.source_query.startswith("site:jobs.lever.co")
