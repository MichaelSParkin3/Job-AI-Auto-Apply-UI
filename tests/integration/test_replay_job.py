"""Integration test: replay-job resets to IN_PROGRESS without browser."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.application_queue import (
    ApplicationItem,
    ApplicationQueue,
    ApplicationStatus,
)
from job_ai_auto_apply_ui.orchestrator import replay_job


@pytest.mark.asyncio
async def test_replay_job_resets_status_from_submitted() -> None:
    """Test that replay-job resets a SUBMITTED item to IN_PROGRESS."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create a queue with a SUBMITTED item
        profile_id = "test_replay"
        queue = ApplicationQueue(profile_id, base_dir=base_dir)

        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/submitted-job",
            company="TestCorp",
            title="Submitted Job",
            details=None,
            source_query="test",
            source_rank=1,
        )
        queue.enqueue([item])

        # Mark as submitted
        queue.resume(item.id)  # Set to IN_PROGRESS first
        queue.mark_submitted(item.id, artifacts=None)

        # Verify initial state
        submitted_item = queue.get(item.id)
        assert submitted_item is not None
        assert submitted_item.status == ApplicationStatus.SUBMITTED

        # Call replay_job
        result = replay_job(item.id)

        # Assertions
        assert result["id"] == item.id
        assert result["status"] == "in_progress"

        # Verify queue was updated
        reloaded = ApplicationQueue(profile_id, base_dir=base_dir)
        replayed_item = reloaded.get(item.id)
        assert replayed_item is not None
        assert replayed_item.status == ApplicationStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_replay_job_resets_status_from_failed() -> None:
    """Test that replay-job resets a FAILED item to IN_PROGRESS."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create a queue with a FAILED item
        profile_id = "test_replay"
        queue = ApplicationQueue(profile_id, base_dir=base_dir)

        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/failed-job",
            company="TestCorp",
            title="Failed Job",
            details=None,
            source_query="test",
            source_rank=1,
        )
        queue.enqueue([item])

        # Mark as failed
        queue.resume(item.id)  # Set to IN_PROGRESS first
        from job_ai_auto_apply_ui.application_queue import Reason

        queue.mark_failed(item.id, Reason(code="test_error", message="Test failure"))

        # Verify initial state
        failed_item = queue.get(item.id)
        assert failed_item is not None
        assert failed_item.status == ApplicationStatus.FAILED

        # Call replay_job
        result = replay_job(item.id)

        # Assertions
        assert result["id"] == item.id
        assert result["status"] == "in_progress"

        # Verify queue was updated
        reloaded = ApplicationQueue(profile_id, base_dir=base_dir)
        replayed_item = reloaded.get(item.id)
        assert replayed_item is not None
        assert replayed_item.status == ApplicationStatus.IN_PROGRESS


@pytest.mark.asyncio
async def test_replay_job_does_not_open_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that replay-job does NOT open a browser session."""

    # Setup temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create a queue with a SUBMITTED item
        profile_id = "test_replay"
        queue = ApplicationQueue(profile_id, base_dir=base_dir)

        item = ApplicationItem.new_from_discovery(
            url="https://jobs.lever.co/test/no-browser-job",
            company="TestCorp",
            title="No Browser Job",
            details=None,
            source_query="test",
            source_rank=1,
        )
        queue.enqueue([item])
        queue.resume(item.id)
        queue.mark_submitted(item.id, artifacts=None)

        # Track if browser session is created
        browser_created = False

        def mock_browser_session(*args, **kwargs):
            nonlocal browser_created
            browser_created = True
            raise AssertionError("replay_job should NOT create browser session")

        # Mock browser session creation (if it was imported)
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.orchestrator.BrowserSession",
            mock_browser_session,
            raising=False,
        )

        # Call replay_job - should NOT trigger browser
        result = replay_job(item.id)

        # Assertions
        assert not browser_created, "Browser session was unexpectedly created"
        assert result["status"] == "in_progress"


@pytest.mark.asyncio
async def test_replay_job_raises_on_missing_item() -> None:
    """Test that replay-job raises LookupError when item is not found."""

    # Setup temp directory with empty queue
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        queue_dir = base_dir / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        profile_id = "test_replay"
        _queue = ApplicationQueue(profile_id, base_dir=base_dir)

        # Try to replay non-existent item
        with pytest.raises(LookupError):
            replay_job("nonexistent-id-12345")
