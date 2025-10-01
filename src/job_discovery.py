"""Job discovery helpers for Google + Lever workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable, Tuple
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from .application_queue import EmploymentType, JobDetails, WorkModel


def build_search_url(keywords: Iterable[str], window_hours: int, cap: int = 10) -> str:
    """Construct a Google search URL for Lever postings."""
    normalized_keywords = [word.strip() for word in keywords if word.strip()]
    query = "site:jobs.lever.co " + " ".join(normalized_keywords)
    params = {
        "q": query.strip(),
        "tbs": _window_to_tbs(window_hours),
        "num": str(max(1, min(int(cap), 50))),
        "hl": "en",
        "filter": "0",
    }
    return "https://www.google.com/search?" + urlencode(params)


def extract_posting_details(
    *,
    html: str,
    base_url: str,
    source_query: str | None = None,
    source_rank: int | None = None,
) -> dict:
    """Parse Lever posting HTML and normalize into a dictionary."""
    soup = BeautifulSoup(html, "html.parser")

    title = _text_or_default(soup.select_one(".posting-headline h2"), default="")
    location = _text_or_default(soup.select_one(".posting-categories .location"))
    department = _clean_category(
        _text_or_default(soup.select_one(".posting-categories .department"))
    )
    commitment = _text_or_default(
        soup.select_one(".posting-categories .commitment")
    )
    workplace = _text_or_default(
        soup.select_one(".posting-categories .workplaceTypes")
    )

    description_el = soup.select_one('[data-qa="job-description"]')
    paragraphs = list(description_el.stripped_strings) if description_el else []
    posting_excerpt = _truncate(" ".join(paragraphs), 1500)
    posting_text = _truncate("\n\n".join(paragraphs), 8192)

    apply_el = soup.select_one("a.postings-btn.template-btn-submit[href*='/apply']")
    apply_url = urljoin(base_url, apply_el["href"]) if apply_el and apply_el.has_attr("href") else None

    details = {
        "title": title,
        "location": location,
        "department": department,
        "employment_type": _map_employment_type(commitment),
        "work_model": _map_work_model(workplace),
        "posting_excerpt": posting_excerpt,
        "posting_text": posting_text,
        "apply_url": apply_url,
        "source_query": source_query,
        "source_rank": source_rank,
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    return details


def to_job_details(payload: dict) -> Tuple[str, JobDetails]:
    """Convert dictionary payload to `(title, JobDetails)` pair."""
    title = payload.get("title", "")
    job_details = JobDetails(
        location=payload.get("location"),
        department=payload.get("department"),
        employment_type=EmploymentType(payload.get("employment_type", "unknown")),
        work_model=WorkModel(payload.get("work_model", "unknown")),
        posting_excerpt=payload.get("posting_excerpt", ""),
        posting_text=payload.get("posting_text", ""),
        apply_url=payload.get("apply_url"),
        source_query=payload.get("source_query"),
        source_rank=payload.get("source_rank"),
    )
    return title, job_details


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _window_to_tbs(window_hours: int) -> str:
    if window_hours <= 1:
        return "qdr:h"
    if window_hours <= 24:
        return "qdr:d"
    if window_hours <= 24 * 7:
        return "qdr:w"
    if window_hours <= 24 * 30:
        return "qdr:m"
    return "qdr:y"


def _text_or_default(element, default: str | None = None) -> str | None:
    if not element:
        return default
    text = element.get_text(strip=True)
    return text or default


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def _map_employment_type(text: str | None) -> str:
    if not text:
        return EmploymentType.UNKNOWN.value
    lowered = text.lower()
    if "full" in lowered:
        return EmploymentType.FULL_TIME.value
    if "part" in lowered:
        return EmploymentType.PART_TIME.value
    if "contract" in lowered:
        return EmploymentType.CONTRACT.value
    if "intern" in lowered:
        return EmploymentType.INTERN.value
    if "temp" in lowered:
        return EmploymentType.TEMPORARY.value
    return EmploymentType.UNKNOWN.value


def _map_work_model(text: str | None) -> str:
    if not text:
        return WorkModel.UNKNOWN.value
    lowered = text.lower()
    if "remote" in lowered:
        return WorkModel.REMOTE.value
    if "hybrid" in lowered:
        return WorkModel.HYBRID.value
    if "on-site" in lowered or "onsite" in lowered:
        return WorkModel.ONSITE.value
    return WorkModel.UNKNOWN.value


def _clean_category(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().rstrip("/").strip()
