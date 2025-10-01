"""Integration tests for building Google discovery URLs."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from src import job_discovery


@pytest.mark.parametrize(
    "window_hours, expected_tbs",
    [
        (24, "qdr:d"),
        (1, "qdr:h"),
        (168, "qdr:w"),
    ],
)
def test_build_search_url_uses_time_filter(
    window_hours: int, expected_tbs: str
) -> None:
    """The Google search URL encodes window via `tbs` parameter."""
    url = job_discovery.build_search_url(
        keywords=["frontend", "react"], window_hours=window_hours, cap=10
    )

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "www.google.com"
    assert parsed.path == "/search"

    params = parse_qs(parsed.query)
    assert params["q"] == ["site:jobs.lever.co frontend react"]
    assert params["tbs"] == [expected_tbs]
    assert params["num"] == ["10"]


def test_build_search_url_includes_language_safety_defaults() -> None:
    """URL includes safe defaults for language and results dedupe."""
    url = job_discovery.build_search_url(
        keywords=["python", "engineer"], window_hours=24, cap=5
    )

    params = parse_qs(urlparse(url).query)
    assert params["hl"] == ["en"]
    assert params["filter"] == ["0"]
    assert params["num"] == ["5"]
