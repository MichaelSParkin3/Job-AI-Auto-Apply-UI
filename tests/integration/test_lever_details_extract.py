from pathlib import Path

from job_ai_auto_apply_ui.job_discovery import build_search_url, discover_jobs
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

    search_url = build_search_url(profile, 24)
    html_map = {
        search_url: search_html,
        "https://jobs.lever.co/example/123": posting_html,
    }
    stub_session = _StubBrowserSession(html_map)

    items = discover_jobs(
        profile=profile,
        window_hours=24,
        cap=3,
        browser_factory=lambda _: stub_session,
    )

    assert len(items) == 1
    item = items[0]
    assert item.details is not None
    assert item.details.location == "Manila"
    assert item.details.apply_url.endswith("/apply")
    assert item.details.posting_excerpt
    assert item.details.source_rank == 1
    assert item.details.source_query.startswith("site:jobs.lever.co")


class _StubPage:
    def __init__(self, session: "_StubBrowserSession") -> None:
        self._session = session
        self.current_url: str | None = None

    async def goto(self, url: str) -> None:
        self.current_url = url
        self._session._record_visit(url)

    async def get_elements_by_css_selector(self, selector: str) -> list[object]:
        html = self._session.html_for(self.current_url)
        if "div.g" in selector or "div.MjjYud" in selector:
            if "class=\"g\"" in html or "class='g'" in html:
                return [object()]
            return []
        return [object()] if html else []

    async def evaluate(self, script: str) -> str:
        return self._session.html_for(self.current_url)

    async def close(self) -> None:  # pragma: no cover - integration helper
        return None


class _StubBrowserSession:
    channel = "chrome"

    def __init__(self, html_by_url: dict[str, str]) -> None:
        self._html_by_url = html_by_url
        self.started = False
        self.stopped = False
        self.visits: list[str] = []
        self._current_page: _StubPage | None = None

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def get_current_page(self) -> _StubPage | None:
        return self._current_page

    async def new_page(self) -> _StubPage:
        page = _StubPage(self)
        if self._current_page is None:
            self._current_page = page
        return page

    def html_for(self, url: str | None) -> str:
        if not url:
            return ""
        return self._html_by_url.get(url, "")

    def _record_visit(self, url: str) -> None:
        self.visits.append(url)
