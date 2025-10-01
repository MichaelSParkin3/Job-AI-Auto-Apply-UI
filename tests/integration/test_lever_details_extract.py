"""Integration tests for extracting Lever posting details."""

from __future__ import annotations

from pathlib import Path

import pytest

from src import job_discovery


@pytest.fixture()
def lever_posting_html() -> str:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "lever_posting.html"
    return fixture_path.read_text(encoding="utf-8")


def test_extract_posting_details_normalizes_fields(lever_posting_html: str) -> None:
    """Extraction normalizes enums and trims whitespace from Lever content."""
    details = job_discovery.extract_posting_details(
        html=lever_posting_html,
        base_url="https://example.jobs.lever.co/wordpress-developer",
        source_query="site:jobs.lever.co wordpress",
        source_rank=1,
    )

    assert details["title"] == "WordPress Developer (Full Time - Work from home)"
    assert details["location"] == "Manila"
    assert details["department"] == "Remote Roles - Philippines"
    assert details["employment_type"] == "full_time"
    assert details["work_model"] == "remote"
    assert details["apply_url"] == "https://example.jobs.lever.co/apply"
    assert details["source_query"] == "site:jobs.lever.co wordpress"
    assert details["source_rank"] == 1
    assert details["posting_excerpt"].startswith("CALLING ALL DEVELOPERS")
    assert "WordPress Developer" in details["posting_text"]
    assert len(details["posting_excerpt"]) <= 1500
    assert len(details["posting_text"]) <= 8192
