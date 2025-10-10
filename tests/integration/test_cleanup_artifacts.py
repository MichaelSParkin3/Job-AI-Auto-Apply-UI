"""Integration test: cleanup-artifacts deletes only targeted files."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.application_queue import ApplicationItem, ApplicationQueue


def _create_artifact_file(path: Path, age_days: int) -> None:
    """Create an artifact file with a specific age."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test artifact content", encoding="utf-8")

    # Set file modification time to simulate age
    timestamp = (datetime.now(UTC) - timedelta(days=age_days)).timestamp()
    import os

    os.utime(path, (timestamp, timestamp))


@pytest.mark.asyncio
async def test_cleanup_artifacts_dry_run_lists_without_deleting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test cleanup-artifacts --dry-run lists matched files without deleting them."""

    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir) / "artifacts"

        # Create artifacts of various ages
        profile1_dir = artifacts_dir / "profile1"
        item1_dir = profile1_dir / "item001"
        item2_dir = profile1_dir / "item002"

        # Old artifacts (60 days)
        _create_artifact_file(item1_dir / "pre.json", age_days=60)
        _create_artifact_file(item1_dir / "pre-full.jpg", age_days=60)

        # Recent artifacts (10 days)
        _create_artifact_file(item2_dir / "pre.json", age_days=10)
        _create_artifact_file(item2_dir / "pre-full.jpg", age_days=10)

        # NOTE: This test will FAIL until T014 (cleanup-artifacts command)

        # Expected behavior with --dry-run --older-than 30:
        # 1. Scan artifacts_dir for files
        # 2. Filter by modification time (>30 days old)
        # 3. Return matched files list without deleting
        # 4. JSON output: {
        #      "matched": 2,
        #      "files": ["...item001/pre.json", "...item001/pre-full.jpg"],
        #      "deleted": 0
        #    }
        # 5. Exit code: 0

        # Verify files still exist after dry-run
        assert (item1_dir / "pre.json").exists()
        assert (item1_dir / "pre-full.jpg").exists()

        # Placeholder assertion
        assert False, "Cleanup-artifacts --dry-run not yet implemented"


@pytest.mark.asyncio
async def test_cleanup_artifacts_deletes_old_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test cleanup-artifacts deletes files older than specified days."""

    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir) / "artifacts"

        # Create artifacts
        profile1_dir = artifacts_dir / "profile1"
        item1_dir = profile1_dir / "item001"
        item2_dir = profile1_dir / "item002"

        # Old artifacts (60 days)
        old_file1 = item1_dir / "pre.json"
        old_file2 = item1_dir / "pre-full.jpg"
        _create_artifact_file(old_file1, age_days=60)
        _create_artifact_file(old_file2, age_days=60)

        # Recent artifacts (10 days)
        recent_file1 = item2_dir / "pre.json"
        recent_file2 = item2_dir / "pre-full.jpg"
        _create_artifact_file(recent_file1, age_days=10)
        _create_artifact_file(recent_file2, age_days=10)

        # NOTE: This test will FAIL until T014 implementation

        # Expected behavior with --older-than 30 (no --dry-run):
        # 1. Scan and filter files >30 days
        # 2. Delete matched files
        # 3. JSON output: {"matched": 2, "deleted": 2}
        # 4. Exit code: 0

        # Verify only old files deleted
        assert not old_file1.exists(), "Old pre.json should be deleted"
        assert not old_file2.exists(), "Old pre-full.jpg should be deleted"
        assert recent_file1.exists(), "Recent pre.json should NOT be deleted"
        assert recent_file2.exists(), "Recent pre-full.jpg should NOT be deleted"

        # Placeholder assertion
        assert False, "Cleanup-artifacts deletion not yet implemented"


@pytest.mark.asyncio
async def test_cleanup_artifacts_profile_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test cleanup-artifacts --profile filters to specific profile only."""

    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir) / "artifacts"

        # Create artifacts for multiple profiles
        profile1_dir = artifacts_dir / "profile1"
        profile2_dir = artifacts_dir / "profile2"

        # Old artifacts in both profiles
        p1_file = profile1_dir / "item001" / "pre.json"
        p2_file = profile2_dir / "item001" / "pre.json"
        _create_artifact_file(p1_file, age_days=60)
        _create_artifact_file(p2_file, age_days=60)

        # NOTE: This test will FAIL until T014 implementation

        # Expected behavior with --profile profile1 --older-than 30:
        # 1. Only scan artifacts_dir/profile1/
        # 2. Delete old files in profile1 only
        # 3. profile2 artifacts remain untouched

        # Verify profile filtering
        assert not p1_file.exists(), "profile1 artifact should be deleted"
        assert p2_file.exists(), "profile2 artifact should NOT be deleted"

        # Placeholder assertion
        assert False, "Cleanup-artifacts --profile filter not yet implemented"


@pytest.mark.asyncio
async def test_cleanup_artifacts_preserves_queue_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test cleanup-artifacts does NOT delete queue JSON files."""

    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir) / "artifacts"
        queue_dir = Path(tmpdir) / "queues"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Create old artifacts
        item_dir = artifacts_dir / "profile1" / "item001"
        artifact_file = item_dir / "pre.json"
        _create_artifact_file(artifact_file, age_days=60)

        # Create queue file
        queue_file = queue_dir / "profile1.json"
        queue_data = {
            "items": [
                {
                    "id": "item001",
                    "url": "https://jobs.lever.co/test/job",
                    "status": "submitted",
                }
            ]
        }
        queue_file.write_text(json.dumps(queue_data), encoding="utf-8")

        # Set queue file to old age too
        timestamp = (datetime.now(UTC) - timedelta(days=60)).timestamp()
        import os

        os.utime(queue_file, (timestamp, timestamp))

        # NOTE: This test will FAIL until T014 implementation

        # Expected behavior:
        # 1. cleanup-artifacts only targets data/artifacts/ directory
        # 2. Queue files in data/queues/ are never touched
        # 3. Even if queue files are old, they remain

        # Verify queue file preserved
        assert queue_file.exists(), "Queue file should NOT be deleted"
        assert not artifact_file.exists(), "Artifact should be deleted"

        # Placeholder assertion
        assert False, "Cleanup queue preservation not yet implemented"


@pytest.mark.asyncio
async def test_cleanup_artifacts_nothing_matched_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test cleanup-artifacts returns exit code 2 when nothing matched."""

    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir) / "artifacts"

        # Create only recent artifacts
        item_dir = artifacts_dir / "profile1" / "item001"
        _create_artifact_file(item_dir / "pre.json", age_days=5)

        # NOTE: This test will FAIL until T014 implementation

        # Expected behavior with --older-than 30 when no files match:
        # 1. Scan for files >30 days
        # 2. Find 0 matches
        # 3. JSON output: {"matched": 0, "deleted": 0}
        # 4. Exit code: 2 (nothing matched)

        # Placeholder assertion
        assert False, "Cleanup nothing-matched exit code not yet implemented"


@pytest.mark.asyncio
async def test_cleanup_artifacts_requires_older_than_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test cleanup-artifacts rejects invocation without --older-than."""

    # NOTE: This test will FAIL until T014 implementation

    # Expected behavior when --older-than is missing:
    # 1. Argument parser validation fails
    # 2. Error message: "--older-than is required"
    # 3. Exit code: 5 (invalid args)

    # Placeholder assertion
    assert False, "Cleanup --older-than requirement not yet implemented"


@pytest.mark.asyncio
async def test_cleanup_artifacts_json_output_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test cleanup-artifacts --json outputs correct JSON structure."""

    with tempfile.TemporaryDirectory() as tmpdir:
        artifacts_dir = Path(tmpdir) / "artifacts"

        # Create old artifacts
        item_dir = artifacts_dir / "profile1" / "item001"
        _create_artifact_file(item_dir / "pre.json", age_days=60)
        _create_artifact_file(item_dir / "pre-full.jpg", age_days=60)

        # NOTE: This test will FAIL until T014 implementation

        # Expected JSON output format:
        # {
        #   "matched": 2,
        #   "deleted": 2,  // 0 if --dry-run
        #   "files": [...]  // included in --dry-run
        # }

        # Placeholder assertion
        assert False, "Cleanup JSON output format not yet implemented"
