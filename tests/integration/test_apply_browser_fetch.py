from __future__ import annotations

from pathlib import Path

from job_ai_auto_apply_ui.application_queue import ApplicationItem, ApplicationQueue, JobDetails
from job_ai_auto_apply_ui.orchestrator import iter_apply_events
from job_ai_auto_apply_ui.profile_manager import Profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_iter_apply_events_uses_browser_session(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    profile = Profile(
        id="front_end",
        name="Front End",
        resume_path=Path("resume.pdf"),
        defaults={},
        keywords={},
        prompts={},
    )

    queue = ApplicationQueue(profile.id)
    apply_url = "https://jobs.lever.co/example/123/apply"
    details = JobDetails(apply_url=apply_url)
    item = ApplicationItem.new_from_discovery(
        url="https://jobs.lever.co/example/123",
        company="example",
        title="Senior Frontend Engineer",
        details=details,
    )
    queue.enqueue([item])

    form_html = (FIXTURES / "lever_form.html").read_text(encoding="utf-8")
    stub_session = _StubApplyBrowserSession(form_html)

    events = list(
        iter_apply_events(
            profile,
            "auto",
            browser_factory=lambda prof, opts: stub_session,
        )
    )

    assert stub_session.started is True
    assert stub_session.stopped is True
    assert stub_session.visited_urls == [apply_url]
    assert any(event["event"] == "submitted" for event in events)


class _StubApplyPage:
    def __init__(self, session: "_StubApplyBrowserSession", html: str) -> None:
        self._session = session
        self._html = html
        self.current_url: str | None = None

    async def goto(self, url: str) -> None:
        self.current_url = url
        self._session.visited_urls.append(url)

    async def evaluate(self, script: str) -> str:
        return self._html

    async def close(self) -> None:  # pragma: no cover - helper
        return None


class _StubApplyBrowserSession:
    channel = "chrome"

    def __init__(self, html: str) -> None:
        self._html = html
        self.started = False
        self.stopped = False
        self.visited_urls: list[str] = []
        self._page: _StubApplyPage | None = None

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def get_current_page(self) -> _StubApplyPage | None:
        return self._page

    async def new_page(self) -> _StubApplyPage:
        page = _StubApplyPage(self, self._html)
        if self._page is None:
            self._page = page
        return page
