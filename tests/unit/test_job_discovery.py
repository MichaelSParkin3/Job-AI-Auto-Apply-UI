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
    assert query.startswith("site:jobs.lever.co (")
    assert query.count('"') == 12  # 6 quoted terms
    assert query.count(" OR ") == 5
    assert query.endswith(")")


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


class _StubPage:
    def __init__(self, html: str) -> None:
        self.html = html
        self.visited_urls: list[str] = []

    async def goto(self, url: str) -> None:
        self.visited_urls.append(url)

    async def get_elements_by_css_selector(self, selector: str) -> list[object]:
        return [object()]

    async def evaluate(self, script: str) -> str:
        return self.html


class _StubBrowserSession:
    channel = "chrome"

    def __init__(self, html: str) -> None:
        self.page = _StubPage(html)
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def get_current_page(self) -> _StubPage:  # pragma: no cover - exercised indirectly
        return self.page

    async def new_page(self) -> _StubPage:  # pragma: no cover - exercised indirectly
        return self.page


def test_discover_jobs_uses_browser_session(monkeypatch) -> None:
    monkeypatch.setenv("AUTO_APPLY_BROWSER_MODE", "auto")
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

    stub_session = _StubBrowserSession(search_html)

    items = discover_jobs(
        profile=profile,
        window_hours=24,
        cap=5,
        fetch_posting=lambda url: posting_html,
        browser_factory=lambda _: stub_session,
    )

    assert stub_session.started is True
    assert stub_session.stopped is True
    # Browser-based discovery now visits both search URL and posting URLs
    expected_search_url = build_search_url(profile, 24)
    assert stub_session.page.visited_urls[0] == expected_search_url
    assert len(stub_session.page.visited_urls) == 2  # search + posting
    assert "jobs.lever.co/example/123" in stub_session.page.visited_urls[1]
    assert len(items) == 1
