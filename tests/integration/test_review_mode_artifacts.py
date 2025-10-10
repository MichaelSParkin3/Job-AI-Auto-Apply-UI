"""Integration test: review-mode persists pre.json + pre-full.jpg and sets pending_review."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from job_ai_auto_apply_ui.application_queue import ApplicationItem, ApplicationQueue, ApplicationStatus
from job_ai_auto_apply_ui.profile_manager import Profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _test_profile() -> Profile:
    """Create a test profile for integration testing."""
    return Profile(
        id="test_review",
        name="Test Review Profile",
        resume_path=Path("tests/fixtures/test_resume.pdf"),
        defaults={"name": "Test User", "email": "test@example.com"},
        keywords={"roles": ["Engineer"]},
        prompts={},
    )


class _StubPage:
    """Stub Playwright page for testing without browser."""

    def __init__(self, html: str = ""):
        self.html = html
        self.visited_urls: list[str] = []
        self.screenshots: list[tuple[Path, dict]] = []

    async def goto(self, url: str) -> None:
        self.visited_urls.append(url)

    async def evaluate(self, script: str, *args) -> str:
        return self.html

    async def screenshot(self, **kwargs) -> bytes:
        # Record screenshot call
        path = kwargs.get("path")
        self.screenshots.append((path, kwargs))
        # Return fake JPEG bytes
        return b'\xff\xd8\xff\xe0' + b'\x00' * 100  # Minimal JPEG header + padding

    async def content(self) -> str:
        return self.html


class _StubBrowserSession:
    """Stub browser session for testing."""

    def __init__(self, html: str = ""):
        self.page = _StubPage(html)
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def get_current_page(self) -> _StubPage:
        return self.page

    async def new_page(self) -> _StubPage:
        return self.page


@pytest.mark.asyncio
async def test_review_mode_persists_pre_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that review mode saves pre.json and pre-full.jpg, sets status to pending_review."""

    # Setup temp directory for artifacts
    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir)
        profile = _test_profile()

        # Create queue in temp location
        queue_dir = artifacts_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)
        queue_path = queue_dir / f"{profile.id}.json"

        # Create a test application item
        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/job123",
            company="TestCorp",
            title="Senior Engineer",
            details=None,
            source_query="test query",
            source_rank=1,
        )

        # Initialize queue with item
        queue_data = {"items": [item.to_dict()]}
        queue_path.write_text(json.dumps(queue_data), encoding="utf-8")

        # Mock artifacts_path to use temp directory
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.config.Settings.artifacts_path",
            lambda self, profile_id=None: artifacts_dir / "artifacts" / (profile_id or ""),
        )

        # Expected artifact paths
        item_artifact_dir = artifacts_dir / "artifacts" / profile.id / item.id
        pre_json_path = item_artifact_dir / "pre.json"
        pre_screenshot_path = item_artifact_dir / "pre-full.jpg"

        # NOTE: This test will FAIL until T008-T016 are implemented
        # For now, we're verifying the test structure is correct

        # When review mode is implemented, it should:
        # 1. Create item_artifact_dir
        # 2. Write pre.json with SavedState v1 schema
        # 3. Capture full-page screenshot to pre-full.jpg
        # 4. Set queue item status to pending_review

        # Assertions (will fail until implemented):
        assert item_artifact_dir.exists(), "Artifact directory should be created"
        assert pre_json_path.exists(), "pre.json should be saved"
        assert pre_screenshot_path.exists(), "pre-full.jpg should be saved"

        # Verify pre.json structure
        saved_state = json.loads(pre_json_path.read_text(encoding="utf-8"))
        assert saved_state["version"] == "v1"
        assert saved_state["profile_id"] == profile.id
        assert saved_state["item_id"] == item.id
        assert "plan" in saved_state
        assert "values" in saved_state

        # Verify queue status updated
        queue = ApplicationQueue(profile.id)
        updated_item = queue.get(item.id)
        assert updated_item is not None
        assert updated_item.status == ApplicationStatus.PENDING_REVIEW


@pytest.mark.asyncio
async def test_review_mode_emits_saved_for_review_event(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that review mode emits saved_for_review JSON event with correct fields."""

    # Setup
    profile = _test_profile()

    # NOTE: This test will FAIL until orchestrator review-mode implementation
    # Expected event structure:
    expected_event = {
        "event": "saved_for_review",
        "id": "01HXYZ",  # Application item ID
        "form_state_path": "data/artifacts/test_review/01HXYZ/pre.json",
        "screenshot_before_path": "data/artifacts/test_review/01HXYZ/pre-full.jpg",
    }

    # When implemented, verify event is emitted during iter_apply_events
    # with --review-mode flag

    # Placeholder assertion (will fail)
    assert False, "Review mode event emission not yet implemented"


@pytest.mark.asyncio
async def test_review_mode_skips_submission(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that review mode fills form but skips submit button click."""

    # NOTE: This test will FAIL until browser agent review-mode implementation

    # Expected behavior:
    # 1. Form fields are filled with profile defaults
    # 2. Resume is uploaded
    # 3. Form validation passes
    # 4. Submit button is NOT clicked
    # 5. Artifacts are saved
    # 6. Status set to pending_review

    # Placeholder assertion (will fail)
    assert False, "Review mode submission skip not yet implemented"
