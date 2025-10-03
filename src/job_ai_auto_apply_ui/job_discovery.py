"""Job discovery utilities for Lever postings via Google search."""

from __future__ import annotations

import asyncio
import html
import io
import logging
import os
import time
from collections.abc import Callable
import json
from contextlib import redirect_stdout, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import httpx
from browser_use.browser.session import BrowserSession
from .browser_agent import LeverBrowserOptions

from .application_queue import ApplicationItem, JobDetails
from .profile_manager import Profile
from .telemetry import log_event

LOGGER = logging.getLogger(__name__)

_BROWSER_TIMEOUT_SECONDS = 8.0
# Total discovery timeout when also visiting postings via browser
_BROWSER_DISCOVERY_TIMEOUT_SECONDS = 45.0
_BROWSER_DISABLED_MODES = {"off", "disabled", "http"}


@dataclass(slots=True)
class GoogleSearchResult:
    """Normalized representation of a Google result."""

    url: str
    title: str
    snippet: str | None
    rank: int

    def company_slug(self) -> str:
        """Return the Lever company slug inferred from the URL."""
        parsed = urlparse(self.url)
        parts = [segment for segment in parsed.path.split("/") if segment]
        if not parts:
            return parsed.netloc
        return parts[0]


class _GoogleResultsParser(HTMLParser):
    """Minimal parser that extracts Lever results from a Google results page."""

    TARGET_DOMAIN: ClassVar[str] = "jobs.lever.co"

    def __init__(self) -> None:
        super().__init__()
        self._results: list[GoogleSearchResult] = []
        self._inside_anchor = False
        self._current_href: str | None = None
        self._current_title_parts: list[str] = []
        self._capture_snippet = False
        self._snippet_parts: list[str] = []

    @property
    def results(self) -> list[GoogleSearchResult]:
        return self._results

    # HTMLParser overrides -------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: D401 - HTMLParser signature
        attr_map = dict(attrs)
        if tag == "a":
            href = attr_map.get("href")
            if href and self._is_lever_link(href):
                self._inside_anchor = True
                self._current_href = self._strip_tracking_prefix(href)
                self._current_title_parts = []
        elif tag == "div":
            class_attr = attr_map.get("class", "")
            if "VwiC3b" in class_attr or "g0jFAf" in class_attr:
                self._capture_snippet = True
                self._snippet_parts = []

    def handle_endtag(self, tag: str) -> None:  # noqa: D401 - HTMLParser signature
        if tag == "a" and self._inside_anchor:
            title = " ".join(part.strip() for part in self._current_title_parts if part).strip()
            if self._current_href and title:
                snippet = " ".join(part.strip() for part in self._snippet_parts if part).strip()
                self._results.append(
                    GoogleSearchResult(
                        url=self._current_href,
                        title=html.unescape(title),
                        snippet=html.unescape(snippet) if snippet else None,
                        rank=len(self._results) + 1,
                    )
                )
            self._inside_anchor = False
            self._current_href = None
            self._current_title_parts = []
            self._snippet_parts = []
            self._capture_snippet = False
        elif tag == "div" and self._capture_snippet:
            self._capture_snippet = False

    def handle_data(self, data: str) -> None:  # noqa: D401 - HTMLParser signature
        if self._inside_anchor:
            self._current_title_parts.append(data)
        elif self._capture_snippet:
            self._snippet_parts.append(data)

    # Helpers --------------------------------------------------------------
    @classmethod
    def _is_lever_link(cls, href: str) -> bool:
        """Return True only for links that actually resolve to jobs.lever.co.

        Accepts:
        - Absolute http(s) links where host ends with jobs.lever.co
        - Google "/url" wrappers whose q= target host ends with jobs.lever.co
        Rejects everything else (including /search links and login redirects).
        """
        parsed = urlparse(href)
        # Google results often use /url?q=...
        if parsed.path.startswith("/url"):
            params = parse_qs(parsed.query)
            target = params.get("q", [""])[0]
            if not target:
                return False
            t = urlparse(target)
            return bool(t.scheme in {"http", "https"} and t.netloc.endswith(cls.TARGET_DOMAIN))
        # Absolute direct link
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return parsed.netloc.endswith(cls.TARGET_DOMAIN)
        return False

    @staticmethod
    def _strip_tracking_prefix(href: str) -> str:
        parsed = urlparse(href)
        if parsed.path.startswith("/url"):
            params = parse_qs(parsed.query)
            target = params.get("q")
            if target:
                return target[0]
        return href


class _LeverPostingParser(HTMLParser):
    """Parser that extracts structured data from a Lever posting page."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.location: str | None = None
        self.department: str | None = None
        self.employment_type: str | None = None
        self.work_model: str | None = None
        self.description_parts: list[str] = []
        self.capture_title = False
        self.capture_description = False
        self._description_depth = 0
        self._categories_depth = 0
        self._current_category: str | None = None
        self.apply_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: D401
        attr_map = dict(attrs)
        if tag == "div":
            class_attr = attr_map.get("class", "")
            if "posting-headline" in class_attr:
                self.capture_title = True
            if "posting-categories" in class_attr:
                self._categories_depth = 1
                self._current_category = None
            elif self._categories_depth > 0:
                self._categories_depth += 1
                if "location" in class_attr:
                    self._current_category = "location"
                elif "department" in class_attr:
                    self._current_category = "department"
                elif "commitment" in class_attr:
                    self._current_category = "employment"
                elif "workplaceTypes" in class_attr:
                    self._current_category = "work_model"
            if attr_map.get("data-qa") == "job-description":
                self.capture_description = True
                self._description_depth = 1
            elif self.capture_description and self._description_depth > 0:
                self._description_depth += 1
        elif tag == "h2" and self.capture_title:
            self.title_parts = []
        elif self.capture_description and self._description_depth > 0:
            self._description_depth += 1
        elif tag == "a":
            class_attr = attr_map.get("class", "") or ""
            if "template-btn-submit" in class_attr and attr_map.get("href"):
                self.apply_href = urljoin(self.base_url, attr_map["href"])

    def handle_endtag(self, tag: str) -> None:  # noqa: D401
        if tag == "h2" and self.capture_title:
            self.capture_title = False
        elif tag == "div" and self._categories_depth > 0:
            self._categories_depth -= 1
            if self._categories_depth == 0:
                self._current_category = None
        elif self.capture_description and self._description_depth > 0:
            self._description_depth -= 1
            if self._description_depth == 0:
                self.capture_description = False

    def handle_data(self, data: str) -> None:  # noqa: D401
        text = data.strip()
        if not text:
            return
        if self.capture_title:
            self.title_parts.append(text)
        elif self.capture_description:
            self.description_parts.append(text)
        elif self._current_category == "location":
            self.location = text
            self._current_category = None
        elif self._current_category == "department":
            self.department = text.rstrip("/")
            self._current_category = None
        elif self._current_category == "employment":
            self.employment_type = text.split("/")[0].strip()
            self._current_category = None
        elif self._current_category == "work_model":
            self.work_model = text
            self._current_category = None

    def build_details(self) -> JobDetails:
        description = "\n".join(self.description_parts)
        excerpt = description[:1500]
        posting_text = description[:8192]
        details = JobDetails(
            location=self.location,
            department=self.department,
            employment_type=(self.employment_type or "unknown").lower(),
            work_model=(self.work_model or "unknown").lower(),
            posting_excerpt=excerpt or None,
            posting_text=posting_text or None,
            apply_url=self.apply_href,
            extracted_at=datetime.now(UTC),
        )
        return details

    def title(self) -> str | None:
        joined = " ".join(self.title_parts).strip()
        return joined or None


def _quote_query_term(term: str) -> str:
    """Return a Google-safe quoted term, escaping embedded quotes."""

    escaped = term.replace('"', '\\"')
    return f'"{escaped}"'


def build_search_query(profile: Profile, *, max_terms: int = 6) -> str:
    """Return the discovery search query for the profile."""

    seen: dict[str, None] = {}
    for term in profile.discovery_terms():
        if term and term not in seen:
            seen[term] = None

    terms = list(seen.keys())[:max_terms]
    if not terms:
        return "site:jobs.lever.co"

    if len(terms) == 1:
        return f"site:jobs.lever.co {_quote_query_term(terms[0])}".strip()

    joined = " OR ".join(_quote_query_term(term) for term in terms)
    return f"site:jobs.lever.co ({joined})"


def build_search_url(profile: Profile, window_hours: int) -> str:
    """Construct a Google search URL with an appropriate time window."""
    query = build_search_query(profile)
    params = {"q": query, "hl": "en"}
    tbs = _window_to_tbs(window_hours)
    if tbs:
        params["tbs"] = tbs
    return f"https://www.google.com/search?{urlencode(params)}"


def discover_jobs(
    *,
    profile: Profile,
    window_hours: int,
    cap: int,
    fetch_search: Callable[[str], str] | None = None,
    fetch_posting: Callable[[str], str] | None = None,
    browser_factory: Callable[[Profile], BrowserSession] | None = None,
) -> list[ApplicationItem]:
    """Discover Lever job postings for the given profile."""
    search_url = build_search_url(profile, window_hours)
    source_query = build_search_query(profile)
    # If a custom fetch_search was injected (tests), use the legacy non-browser path.
    if fetch_search is not None or _browser_mode() in _BROWSER_DISABLED_MODES:
        # Legacy: load results (maybe via injected fetch), then fetch postings via HTTP
        fetch_posting = fetch_posting or _default_fetch
        try:
            html_document = (
                fetch_search(search_url)
                if fetch_search is not None
                else _default_fetch(search_url)
            )
        except Exception as exc:  # pragma: no cover - dependency/network failure
            LOGGER.exception("Failed to fetch Google results: %s", exc)
            log_event("discover.error", profile=profile.id, reason="google_fetch_failed")
            return []

        parser = _GoogleResultsParser()
        parser.feed(html_document)
        results = parser.results[: max(cap, 0)]

        items: list[ApplicationItem] = []
        for result in results:
            parsed_url = urlparse(result.url)
            if parsed_url.scheme not in {"http", "https"}:
                LOGGER.warning("Skipping non-http result URL: %s", result.url)
                log_event(
                    "discover.result_skipped",
                    profile=profile.id,
                    url=result.url,
                    reason="invalid_scheme",
                )
                continue
            try:
                posting_html = fetch_posting(result.url)
            except Exception as exc:  # pragma: no cover - network failure
                LOGGER.warning("Failed to fetch posting %s: %s", result.url, exc)
                log_event(
                    "discover.posting_fetch_failed",
                    profile=profile.id,
                    url=result.url,
                )
                details = JobDetails(source_query=source_query, source_rank=result.rank)
                title = result.title
            else:
                posting_parser = _LeverPostingParser(result.url)
                posting_parser.feed(posting_html)
                details = posting_parser.build_details()
                details.source_query = source_query
                details.source_rank = result.rank
                title = posting_parser.title() or result.title
                if result.snippet and not details.posting_excerpt:
                    details.posting_excerpt = result.snippet
                if details.apply_url is None:
                    details.apply_url = result.url

            company = result.company_slug()
            item = ApplicationItem.new_from_discovery(
                url=result.url,
                company=company,
                title=title,
                details=details,
                source_query=source_query,
                source_rank=result.rank,
            )
            items.append(item)

        log_event(
            "discover.results",
            profile=profile.id,
            found=len(items),
            cap=cap,
            search_url=search_url,
        )
        return items

    # Preferred new path: use a single browser session to load Google and visit postings
    try:
        items = _discover_with_browser_session(
            profile=profile,
            search_url=search_url,
            source_query=source_query,
            cap=cap,
            browser_factory=browser_factory,
        )
    except Exception as exc:  # pragma: no cover - runtime/browser failure
        LOGGER.exception("Browser-based discovery failed: %s", exc)
        log_event(
            "discover.browser_failed",
            profile=profile.id,
            reason=type(exc).__name__,
        )
        return []
    return items

def _discover_with_browser_session(
    *,
    profile: Profile,
    search_url: str,
    source_query: str,
    cap: int,
    browser_factory: Callable[[Profile], BrowserSession] | None,
) -> list[ApplicationItem]:
    """Drive Google and postings via browser-use and extract details from the DOM."""

    factory = browser_factory or _default_browser_factory
    session = factory(profile)
    log_event(
        "discover.browser_start",
        profile=profile.id,
        browser=getattr(session, "channel", None),
    )

    async def _run() -> list[ApplicationItem]:
        await session.start()
        try:
            page = await session.get_current_page() or await session.new_page()
            await page.goto(search_url)
            try:
                await _wait_for_search_results(page)
            except TimeoutError:
                LOGGER.warning("Timed out waiting for Google results to render")
            html_document = await _capture_page_html(page)

            parser = _GoogleResultsParser()
            parser.feed(html_document)
            results = parser.results[: max(cap, 0)]

            items: list[ApplicationItem] = []
            for result in results:
                # Open each posting in a fresh tab to avoid Google result noise
                try:
                    item = await _extract_item_from_posting(session, result, source_query)
                except Exception as exc:  # pragma: no cover - page/runtime issues
                    LOGGER.warning("Failed to open posting %s: %s", result.url, exc)
                    log_event(
                        "discover.posting_fetch_failed",
                        profile=profile.id,
                        url=result.url,
                    )
                    details = JobDetails(source_query=source_query, source_rank=result.rank)
                    title = result.title
                    company = result.company_slug()
                    item = ApplicationItem.new_from_discovery(
                        url=result.url,
                        company=company,
                        title=title,
                        details=details,
                        source_query=source_query,
                        source_rank=result.rank,
                    )
                items.append(item)

            return items
        finally:
            with suppress(Exception):
                await session.stop()

    items = asyncio.run(asyncio.wait_for(_run(), timeout=_BROWSER_DISCOVERY_TIMEOUT_SECONDS))
    log_event(
        "discover.results",
        profile=profile.id,
        found=len(items),
        cap=cap,
        search_url=search_url,
    )
    log_event("discover.browser_complete", profile=profile.id)
    return items

async def _extract_item_from_posting(
    session: BrowserSession,
    result: GoogleSearchResult,
    source_query: str,
) -> ApplicationItem:
    """Open a posting in the browser and extract normalized details."""
    page = await session.new_page()
    await page.goto(result.url)

    # Best-effort: wait briefly for either headline or application form
    try:
        await asyncio.wait_for(
            _wait_for_any_selector(
                page,
                [".posting-headline h2", "form#application-form", "[data-qa='job-description']"],
            ),
            timeout=6.0,
        )
    except asyncio.TimeoutError:
        pass

    # Extract via JS to avoid brittle HTML parsing
    data = await page.evaluate(
        """
        () => {
          const q = (sel) => document.querySelector(sel);
          const t = (el) => (el && el.textContent ? el.textContent.trim() : null);
          const title = t(q('.posting-headline h2')) || (document.title || null);
          const jobLocation = t(q('.posting-categories .location'));
          const department = t(q('.posting-categories .department'));
          const employment = t(q('.posting-categories .commitment'));
          const workModel = t(q('.posting-categories .workplaceTypes'));
          const descEl = q('[data-qa="job-description"]');
          const description = descEl ? descEl.innerText : '';
          const applyEl = q('a.postings-btn.template-btn-submit[href*="/apply"]');
          const locHref = (window && window.location) ? String(window.location.href || window.location) : null;
          const applyUrl = applyEl ? applyEl.href : (locHref && locHref.includes('/apply') ? locHref : null);
          return JSON.stringify({ title, location: jobLocation, department, employment, workModel, description, applyUrl });
        }
        """
    )

    # Coerce evaluate result to dict
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {}
    elif not isinstance(data, dict):
        data = {}

    # Build details
    description = str(data.get("description") or "") if isinstance(data, dict) else ""
    excerpt = description[:1500] if description else None
    posting_text = description[:8192] if description else None
    employment_type = (str(data.get("employment") or "unknown").split("/")[0].strip()).lower()
    work_model = str(data.get("workModel") or "unknown").lower()

    details = JobDetails(
        location=_none_if_empty(data.get("location")),
        department=_none_if_empty(data.get("department")),
        employment_type=employment_type or "unknown",
        work_model=work_model or "unknown",
        posting_excerpt=excerpt,
        posting_text=posting_text,
        apply_url=_none_if_empty(data.get("applyUrl")) or result.url,
        extracted_at=datetime.now(UTC),
        source_query=source_query,
        source_rank=result.rank,
    )

    title = _none_if_empty(data.get("title")) or result.title
    company = result.company_slug()
    item = ApplicationItem.new_from_discovery(
        url=result.url,
        company=company,
        title=title,
        details=details,
        source_query=source_query,
        source_rank=result.rank,
    )
    return item

async def _wait_for_any_selector(page, selectors: list[str]) -> None:
    """Return when any selector appears; no-op if none are found in time."""
    deadline = time.monotonic() + 6.0
    while time.monotonic() < deadline:
        try:
            for sel in selectors:
                els = await page.get_elements_by_css_selector(sel)
                if els:
                    return
        except Exception:
            pass
        await asyncio.sleep(0.3)
    # Let caller decide on timeout handling
    raise asyncio.TimeoutError

def _none_if_empty(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _default_fetch(url: str) -> str:
    """Fetch a URL using httpx and return the response text."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


def _window_to_tbs(window_hours: int) -> str:
    """Map hour window to Google's tbs parameter."""
    if window_hours <= 1:
        return "qdr:h"
    if window_hours <= 24:
        return "qdr:d"
    if window_hours <= 24 * 7:
        return "qdr:w"
    if window_hours <= 24 * 30:
        return "qdr:m"
    if window_hours <= 24 * 365:
        return "qdr:y"
    return ""


def _load_search_results_with_browser(
    *,
    profile: Profile,
    search_url: str,
    browser_factory: Callable[[Profile], BrowserSession] | None,
) -> str:
    """Load Google search results in a visible browser session."""

    factory = browser_factory or _default_browser_factory
    session = factory(profile)
    log_event(
        "discover.browser_start",
        profile=profile.id,
        browser=getattr(session, "channel", None),
    )

    async def _run() -> str:
        await session.start()
        try:
            page = await session.get_current_page()
            if page is None:
                page = await session.new_page()
            await page.goto(search_url)
            try:
                await _wait_for_search_results(page)
            except TimeoutError:
                LOGGER.warning("Timed out waiting for Google results to render")
            html_document = await _capture_page_html(page)
            return html_document
        finally:
            with suppress(Exception):
                await session.stop()

    try:
        html_document = asyncio.run(asyncio.wait_for(_run(), timeout=_BROWSER_TIMEOUT_SECONDS))
    except asyncio.TimeoutError as exc:  # pragma: no cover - runtime/browser failure
        raise TimeoutError("Browser session timed out") from exc
    log_event("discover.browser_complete", profile=profile.id)
    return html_document


def _default_browser_factory(profile: Profile) -> BrowserSession:
    """Return a BrowserSession configured for discovery with stealth settings."""

    channel = _resolve_browser_channel(profile.preferred_browser)
    user_data_dir = str(profile.user_data_dir) if profile.user_data_dir else None
    options = LeverBrowserOptions.from_settings()
    # Narrow allowed domains for discovery specifically
    discovery_domains = [
        "google.com",
        "www.google.com",
        "jobs.lever.co",
    ]
    options.apply_stealth_environment()
    kwargs = {"allowed_domains": discovery_domains}
    return BrowserSession(
        headless=False,
        channel=channel,
        user_data_dir=user_data_dir,
        keep_alive=True,
        **kwargs,
    )


def _resolve_browser_channel(preferred: str | None) -> str | None:
    if not preferred:
        return "chrome"
    normalized = preferred.strip().lower()
    mapping = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "chromium": "chromium",
        "msedge": "msedge",
        "edge": "msedge",
        "microsoft edge": "msedge",
    }
    return mapping.get(normalized, "chrome")


async def _wait_for_search_results(page) -> None:
    """Wait until Google search results render or timeout."""

    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        try:
            results = await page.get_elements_by_css_selector("div.g, div.MjjYud")
        except Exception:  # pragma: no cover - playwright/cdp errors
            results = []
        if results:
            return
        await asyncio.sleep(0.5)
    raise TimeoutError("Google results did not render in time")


async def _capture_page_html(page) -> str:
    """Capture the full HTML for the current page without noisy logs."""

    with redirect_stdout(io.StringIO()):
        html_document = await page.evaluate(
            "() => document.documentElement.outerHTML"
        )
    return html_document


def _browser_mode() -> str:
    return os.environ.get("AUTO_APPLY_BROWSER_MODE", "auto").strip().lower()


__all__ = [
    "discover_jobs",
    "build_search_url",
    "build_search_query",
    "GoogleSearchResult",
]
