"""Integration test: captcha-blocked persists pre artifacts and sets captcha_blocked status."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.application_queue import (
    ApplicationItem,
    ApplicationQueue,
    ApplicationStatus,
)
from job_ai_auto_apply_ui.profile_manager import Profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _test_profile() -> Profile:
    """Create a test profile for integration testing."""
    return Profile(
        id="test_captcha",
        name="Test Captcha Profile",
        resume_path=Path("tests/fixtures/test_resume.pdf"),
        defaults={"name": "Test User", "email": "test@example.com"},
        keywords={"roles": ["Engineer"]},
        prompts={},
    )


@pytest.mark.asyncio
async def test_captcha_blocked_persists_pre_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that captcha detection triggers pre-submit artifact capture."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()

        # Create queue in temp location
        queue_dir = artifacts_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)
        queue_path = queue_dir / f"{profile.id}.json"

        # Create test application item
        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/job-with-captcha",
            company="CaptchaCorp",
            title="Captcha Protected Job",
            details=None,
            source_query="test query",
            source_rank=1,
        )

        # Initialize queue with item
        queue_data = {"items": [item.to_dict()]}
        queue_path.write_text(json.dumps(queue_data), encoding="utf-8")

        # NOTE: This test will FAIL until T015 (browser agent captcha handling)

        # Expected behavior when CAPTCHA detected:
        # 1. Fill form fields normally
        # 2. Attempt to submit
        # 3. Detect hCaptcha iframe (via selector: iframe[src*='hcaptcha'])
        # 4. Before marking as blocked, save artifacts:
        #    - pre.json with current form state
        #    - pre-full.jpg screenshot
        # 5. Set queue item status to CAPTCHA_BLOCKED
        # 6. Emit captcha_blocked event with artifact paths

        # Expected artifact paths
        item_artifact_dir = artifacts_dir / "artifacts" / profile.id / item.id
        _pre_json_path = item_artifact_dir / "pre.json"
        _pre_screenshot_path = item_artifact_dir / "pre-full.jpg"

        # Placeholder assertions (will fail until implemented)
        assert False, "Captcha-blocked artifact capture not yet implemented"


@pytest.mark.asyncio
async def test_captcha_blocked_sets_correct_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that captcha detection sets queue item status to CAPTCHA_BLOCKED."""

    # Setup
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()
        queue_dir = artifacts_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create item in queue
        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/captcha-job",
            company="CaptchaCorp",
            title="Captcha Job",
            details=None,
            source_query="test",
            source_rank=1,
        )

        queue = ApplicationQueue(profile.id)
        queue.enqueue([item])

        # NOTE: This test will FAIL until T015 implementation

        # Expected behavior:
        # 1. Start apply flow
        # 2. Detect captcha
        # 3. Call queue.mark_captcha_blocked(item.id, artifacts)
        # 4. Status transitions: NEW → IN_PROGRESS → CAPTCHA_BLOCKED

        # Verify status
        updated_item = queue.get(item.id)
        assert updated_item is not None
        assert updated_item.status == ApplicationStatus.CAPTCHA_BLOCKED

        # Placeholder assertion
        assert False, "Captcha-blocked status transition not yet implemented"


@pytest.mark.asyncio
async def test_captcha_blocked_emits_correct_event(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that captcha_blocked event includes form_state_path and screenshot_before_path."""

    # NOTE: This test will FAIL until T016 (event wiring)

    # Expected event structure:
    _expected_event = {
        "event": "captcha_blocked",
        "id": "01HXYZ",
        "form_state_path": "data/artifacts/test_captcha/01HXYZ/pre.json",
        "screenshot_before_path": "data/artifacts/test_captcha/01HXYZ/pre-full.jpg",
    }

    # Verify event emitted during iter_apply_events when captcha detected

    # Placeholder assertion
    assert False, "Captcha-blocked event emission not yet implemented"


@pytest.mark.asyncio
async def test_captcha_blocked_allows_resume_after_manual_solve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that captcha-blocked items can be resumed after manual solving."""

    # Setup
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()

        # Create captcha-blocked item with saved artifacts
        item_id = "01HXYZ1234567890"
        item_artifact_dir = artifacts_dir / "artifacts" / profile.id / item_id
        item_artifact_dir.mkdir(parents=True, exist_ok=True)

        # Create pre.json
        saved_state = json.loads((FIXTURES / "pre_state_sample.json").read_text(encoding="utf-8"))
        saved_state["item_id"] = item_id
        (item_artifact_dir / "pre.json").write_text(json.dumps(saved_state), encoding="utf-8")

        # Create pre-full.jpg
        (item_artifact_dir / "pre-full.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        # NOTE: This test will FAIL until T012 (resume-job implementation)

        # Expected behavior:
        # 1. resume-job loads pre.json
        # 2. Opens browser to apply_url
        # 3. Prefills form from saved state
        # 4. User manually solves captcha in headful browser
        # 5. With --submit: proceeds to submission
        # 6. Status transitions: CAPTCHA_BLOCKED → IN_PROGRESS → SUBMITTED

        # Placeholder assertion
        assert False, "Resume after captcha-blocked not yet implemented"


@pytest.mark.asyncio
async def test_captcha_detection_via_selector(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that captcha is detected via iframe[src*='hcaptcha'] selector."""

    # NOTE: This test will FAIL until browser agent captcha detection (T015)

    # Expected behavior:
    # 1. After filling form, check for captcha_selector from plan
    # 2. If hCaptcha iframe is visible: trigger captcha_blocked flow
    # 3. Save artifacts before blocking

    # Test with mock page containing hCaptcha iframe
    _html_with_captcha = """
    <html>
        <body>
            <form id="application-form">
                <input name="name" value="Test">
                <iframe src="https://hcaptcha.com/captcha/v1/abc123"></iframe>
                <button type="submit">Submit</button>
            </form>
        </body>
    </html>
    """

    # Placeholder assertion
    assert False, "hCaptcha iframe detection not yet implemented"
