from pathlib import Path
from urllib.parse import parse_qs, urlparse

from job_ai_auto_apply_ui.job_discovery import build_search_url
from job_ai_auto_apply_ui.profile_manager import Profile


def _profile() -> Profile:
    return Profile(
        id="front_end",
        name="Front End",
        resume_path=Path("resume.pdf"),
        defaults={},
        keywords={"roles": ["Senior Front End Developer", "Staff Frontend Engineer"]},
        prompts={},
    )


def test_build_search_url_encodes_time_filter() -> None:
    profile = _profile()
    url = build_search_url(profile, window_hours=48)

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.netloc == "www.google.com"
    assert params["q"][0].startswith("site:jobs.lever.co")
    assert params["tbs"] == ["qdr:w"]
    assert params["hl"] == ["en"]
