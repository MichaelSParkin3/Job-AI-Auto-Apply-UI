"""Integration test: resume-job prefill + pause; --submit triggers submit path."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.application_queue import ApplicationItem, ApplicationQueue
from job_ai_auto_apply_ui.profile_manager import Profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _test_profile() -> Profile:
    """Create a test profile for integration testing."""
    return Profile(
        id="test_resume",
        name="Test Resume Profile",
        resume_path=Path("tests/fixtures/test_resume.pdf"),
        defaults={"name": "Test User", "email": "test@example.com"},
        keywords={"roles": ["Engineer"]},
        prompts={},
    )


@pytest.mark.asyncio
async def test_resume_job_prefills_from_saved_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that resume-job loads pre.json and prefills form fields."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()
        item_id = "01HXYZ1234567890"

        # Create pre.json fixture
        item_artifact_dir = artifacts_dir / "artifacts" / profile.id / item_id
        item_artifact_dir.mkdir(parents=True, exist_ok=True)

        pre_json_path = item_artifact_dir / "pre.json"
        saved_state = json.loads((FIXTURES / "pre_state_sample.json").read_text(encoding="utf-8"))
        saved_state["profile_id"] = profile.id
        saved_state["item_id"] = item_id
        pre_json_path.write_text(json.dumps(saved_state), encoding="utf-8")

        # Create queue with the item
        queue_dir = artifacts_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)
        queue_path = queue_dir / f"{profile.id}.json"

        item = ApplicationItem.new_from_discovery(
            url=saved_state["url"],
            company="TestCorp",
            title="Senior Engineer",
            details=None,
            source_query="test",
            source_rank=1,
        )
        item.id = item_id  # Override with our known ID
        queue_data = {"items": [item.to_dict()]}
        queue_path.write_text(json.dumps(queue_data), encoding="utf-8")

        # NOTE: This test will FAIL until T012 (resume-job implementation)

        # Expected behavior:
        # 1. Load pre.json from artifacts
        # 2. Open browser to apply_url
        # 3. Apply saved state to prefill all fields:
        #    - Contact fields (name, email, phone, location)
        #    - Link fields (portfolio, github, linkedin)
        #    - Dynamic questions
        #    - EEO fields
        #    - Resume (verify storage_id or filename populated)
        # 4. Pause for manual review (without --submit)

        # Placeholder assertions (will fail)
        assert pre_json_path.exists(), "pre.json fixture should exist"
        assert False, "Resume-job prefill not yet implemented"


@pytest.mark.asyncio
async def test_resume_job_without_submit_pauses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test resume-job without --submit flag pauses for review."""

    # NOTE: This test will FAIL until T012 implementation

    # Expected behavior:
    # 1. Prefill form from pre.json
    # 2. Output status: "paused"
    # 3. Do NOT click submit button
    # 4. Return payload: {"id": "...", "status": "paused", "message": "Review..."}

    # Placeholder assertion
    assert False, "Resume-job pause behavior not yet implemented"


@pytest.mark.asyncio
async def test_resume_job_with_submit_proceeds_to_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test resume-job with --submit flag proceeds to submit and captures confirmation."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()
        item_id = "01HXYZ1234567890"

        # Create pre.json
        item_artifact_dir = artifacts_dir / "artifacts" / profile.id / item_id
        item_artifact_dir.mkdir(parents=True, exist_ok=True)
        pre_json_path = item_artifact_dir / "pre.json"

        saved_state = json.loads((FIXTURES / "pre_state_sample.json").read_text(encoding="utf-8"))
        saved_state["profile_id"] = profile.id
        saved_state["item_id"] = item_id
        pre_json_path.write_text(json.dumps(saved_state), encoding="utf-8")

        # NOTE: This test will FAIL until T012 implementation

        # Expected behavior with --submit:
        # 1. Prefill form from pre.json
        # 2. Click submit button
        # 3. Capture confirmation (text + id)
        # 4. Save post-full.jpg (if --audit-after-submit enabled)
        # 5. Save confirmation.json
        # 6. Update queue status to SUBMITTED
        # 7. Return payload: {
        #      "id": "...",
        #      "status": "submitted",
        #      "confirmation_text": "...",
        #      "confirmation_id": "..."
        #    }

        # Placeholder assertion
        assert False, "Resume-job with --submit not yet implemented"


@pytest.mark.asyncio
async def test_resume_job_missing_pre_json_returns_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test resume-job returns invalid_state error when pre.json is missing."""

    # NOTE: This test will FAIL until T012 implementation

    # Expected behavior:
    # 1. Check for pre.json
    # 2. If missing: return {"id": "...", "status": "invalid_state", "error": "pre.json missing or invalid"}
    # 3. Exit code: 6

    # Placeholder assertion
    assert False, "Resume-job invalid_state handling not yet implemented"


@pytest.mark.asyncio
async def test_resume_job_corrupt_pre_json_returns_invalid_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test resume-job returns invalid_state error when pre.json is corrupt."""

    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()
        item_id = "01HXYZ1234567890"

        # Create corrupt pre.json
        item_artifact_dir = artifacts_dir / "artifacts" / profile.id / item_id
        item_artifact_dir.mkdir(parents=True, exist_ok=True)
        pre_json_path = item_artifact_dir / "pre.json"
        pre_json_path.write_text("{ invalid json content", encoding="utf-8")

        # NOTE: This test will FAIL until T012 implementation

        # Expected behavior:
        # 1. Attempt to parse pre.json
        # 2. Catch JSONDecodeError
        # 3. Return {"id": "...", "status": "invalid_state", "error": "pre.json missing or invalid"}
        # 4. Exit code: 6

        # Placeholder assertion
        assert False, "Resume-job corrupt pre.json handling not yet implemented"
