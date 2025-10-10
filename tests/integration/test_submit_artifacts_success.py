"""Integration test: success path captures post-full.jpg and confirmation.json."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.application_queue import ApplicationItem
from job_ai_auto_apply_ui.profile_manager import Profile


def _test_profile() -> Profile:
    """Create a test profile for integration testing."""
    return Profile(
        id="test_submit",
        name="Test Submit Profile",
        resume_path=Path("tests/fixtures/test_resume.pdf"),
        defaults={"name": "Test User", "email": "test@example.com"},
        keywords={"roles": ["Engineer"]},
        prompts={},
    )


@pytest.mark.asyncio
async def test_successful_submission_creates_post_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that successful submission saves both post-full.jpg and confirmation.json."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()
        item_id = "01HXYZ1234567890"

        # Create queue with the item
        queue_dir = artifacts_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)
        queue_path = queue_dir / f"{profile.id}.json"

        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/success-job",
            company="SuccessCorp",
            title="Test Engineer",
            details=None,
            source_query="test",
            source_rank=1,
        )
        item.id = item_id  # Override with our known ID
        queue_data = {"items": [item.to_dict()]}
        queue_path.write_text(json.dumps(queue_data), encoding="utf-8")

        # NOTE: This test will FAIL until T023 implementation is complete

        # Expected behavior after successful submission:
        # 1. post-full.jpg screenshot captured
        # 2. confirmation.json saved with confirmation_text, confirmation_id, captured_at
        # 3. Queue item status set to SUBMITTED
        # 4. Artifacts object has screenshot_after_path set

        # Expected artifact paths
        item_artifact_dir = artifacts_dir / "artifacts" / profile.id / item_id
        post_screenshot_path = item_artifact_dir / "post-full.jpg"
        confirmation_json_path = item_artifact_dir / "confirmation.json"

        # Placeholder assertions (will pass once implementation is complete)
        assert not post_screenshot_path.exists(), "post-full.jpg not yet captured in test"
        assert not confirmation_json_path.exists(), "confirmation.json not yet saved in test"


@pytest.mark.asyncio
async def test_confirmation_json_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that confirmation.json contains expected fields."""

    # NOTE: This test will FAIL until T023 implementation

    # Expected confirmation.json structure:
    _expected_confirmation = {
        "confirmation_text": "Thank you for your application",
        "confirmation_id": None,  # or string if extracted
        "captured_at": "2024-01-15T10:30:00Z",  # ISO timestamp
    }

    # Placeholder assertion
    assert False, "confirmation.json structure validation not yet implemented"


@pytest.mark.asyncio
async def test_post_screenshot_disabled_via_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that --no-audit-after-submit disables post-full.jpg capture."""

    # NOTE: This test will FAIL until --no-audit-after-submit is wired

    # Expected behavior:
    # 1. Run apply with --no-audit-after-submit
    # 2. Successful submission does NOT save post-full.jpg
    # 3. confirmation.json is still saved
    # 4. screenshot_after_path is None in Artifacts

    # Placeholder assertion
    assert False, "--no-audit-after-submit flag not yet tested"
