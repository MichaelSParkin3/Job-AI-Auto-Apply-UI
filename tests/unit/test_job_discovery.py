from __future__ import annotations

from pathlib import Path

from job_ai_auto_apply_ui.job_discovery import (
    build_search_query,
    build_search_url,
    discover_jobs,
)
from job_ai_auto_apply_ui.profile_manager import Profile


def _profile() -> Profile:
    return Profile(
        id="frontend",
        name="Frontend",
        resume_path=Path("resume.pdf"),
        defaults={},
        keywords={
            "roles": [
                "Senior Front End Developer",
                "Principal Frontend Engineer",
                "Staff Frontend Engineer",
                "Lead UI Engineer",
                "React Developer",
                "Next.js Developer",
                "TypeScript Engineer",
            ]
        },
        prompts={},
    )


def test_build_search_query_limits_terms() -> None:
    query = build_search_query(_profile())
    assert query.startswith("site:jobs.lever.co")
    assert query.count("\"") == 12  # 6 quoted terms


def test_build_search_url_maps_window() -> None:
    profile = _profile()
    url = build_search_url(profile, window_hours=24)
    assert "https://www.google.com/search?" in url
    assert "tbs=qdr%3Ad" in url


def test_discover_jobs_parses_results(monkeypatch) -> None:
    profile = _profile()
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    posting_html = (fixtures / "lever_posting.html").read_text(encoding="utf-8")
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
        cap=5,
        fetch_search=lambda url: search_html,
        fetch_posting=lambda url: posting_html,
    )

    assert len(items) == 1
    item = items[0]
    assert item.company == "example"
    assert item.details is not None
    assert item.details.location == "Manila"
    assert item.details.work_model == "remote"
    assert item.details.employment_type.startswith("full time")
    assert item.details.apply_url.endswith("/apply")
