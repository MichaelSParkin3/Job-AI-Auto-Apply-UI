"""Tests for QueueService with status enum validation."""

import pytest
import json
import tempfile
from pathlib import Path
from src.models import ApplicationItem, ApplicationStatus
from src.services import QueueService


@pytest.fixture
def temp_queues_dir():
    """Create temporary directory for queue files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def queue_service(temp_queues_dir):
    """Create QueueService instance with temporary directory."""
    return QueueService(temp_queues_dir)


class TestApplicationStatusNormalization:
    """Tests for ApplicationStatus.normalize() method."""

    def test_normalize_uppercase_status(self):
        """Test that uppercase status values are unchanged."""
        assert ApplicationStatus.normalize("SUBMITTED") == "SUBMITTED"
        assert ApplicationStatus.normalize("FAILED") == "FAILED"
        assert ApplicationStatus.normalize("NEW") == "NEW"
        assert ApplicationStatus.normalize("IN_PROGRESS") == "IN_PROGRESS"
        assert ApplicationStatus.normalize("CAPTCHA_BLOCKED") == "CAPTCHA_BLOCKED"

    def test_normalize_lowercase_status(self):
        """Test that lowercase status values are converted to uppercase."""
        assert ApplicationStatus.normalize("submitted") == "SUBMITTED"
        assert ApplicationStatus.normalize("failed") == "FAILED"
        assert ApplicationStatus.normalize("new") == "NEW"
        assert ApplicationStatus.normalize("in_progress") == "IN_PROGRESS"
        assert ApplicationStatus.normalize("captcha_blocked") == "CAPTCHA_BLOCKED"

    def test_normalize_mixedcase_status(self):
        """Test that mixed case status values are converted to uppercase."""
        assert ApplicationStatus.normalize("Submitted") == "SUBMITTED"
        assert ApplicationStatus.normalize("FAILED") == "FAILED"
        assert ApplicationStatus.normalize("Failed") == "FAILED"

    def test_normalize_legacy_pending_review(self):
        """Test that legacy 'pending_review' maps to 'SUBMITTED'."""
        assert ApplicationStatus.normalize("pending_review") == "SUBMITTED"
        assert ApplicationStatus.normalize("PENDING_REVIEW") == "SUBMITTED"

    def test_normalize_legacy_skipped(self):
        """Test that legacy 'skipped' maps to 'FAILED'."""
        assert ApplicationStatus.normalize("skipped") == "FAILED"
        assert ApplicationStatus.normalize("SKIPPED") == "FAILED"


class TestQueueServiceLoadQueue:
    """Tests for QueueService.load_queue() with status normalization."""

    def test_load_queue_with_lowercase_statuses(self, queue_service, temp_queues_dir):
        """Test loading queue file with lowercase status values."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        # Create queue file with lowercase statuses (like Python CLI generates)
        queue_data = {
            "items": [
                {
                    "id": "ulid1",
                    "url": "https://jobs.lever.co/company/job1",
                    "company": "Company A",
                    "title": "Software Engineer",
                    "status": "submitted",  # lowercase
                },
                {
                    "id": "ulid2",
                    "url": "https://jobs.lever.co/company/job2",
                    "company": "Company B",
                    "title": "Data Scientist",
                    "status": "failed",  # lowercase
                },
            ]
        }

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        # Load and verify
        items = queue_service.load_queue(profile_id)
        assert len(items) == 2
        assert items[0].status == ApplicationStatus.SUBMITTED
        assert items[1].status == ApplicationStatus.FAILED

    def test_load_queue_with_legacy_statuses(self, queue_service, temp_queues_dir):
        """Test loading queue file with legacy status values."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        queue_data = {
            "items": [
                {
                    "id": "ulid1",
                    "url": "https://jobs.lever.co/company/job1",
                    "company": "Company A",
                    "title": "Engineer",
                    "status": "pending_review",  # legacy value
                },
                {
                    "id": "ulid2",
                    "url": "https://jobs.lever.co/company/job2",
                    "company": "Company B",
                    "title": "Designer",
                    "status": "skipped",  # legacy value
                },
            ]
        }

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        items = queue_service.load_queue(profile_id)
        assert len(items) == 2
        # Legacy "pending_review" should map to "SUBMITTED"
        assert items[0].status == ApplicationStatus.SUBMITTED
        # Legacy "skipped" should map to "FAILED"
        assert items[1].status == ApplicationStatus.FAILED

    def test_load_queue_mixed_case_statuses(self, queue_service, temp_queues_dir):
        """Test loading queue with mixed case statuses."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        queue_data = {
            "items": [
                {
                    "id": "ulid1",
                    "url": "https://jobs.lever.co/company/job1",
                    "company": "Company",
                    "title": "Position",
                    "status": "Submitted",  # mixed case
                },
            ]
        }

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        items = queue_service.load_queue(profile_id)
        assert len(items) == 1
        assert items[0].status == ApplicationStatus.SUBMITTED

    def test_load_queue_empty_file(self, queue_service, temp_queues_dir):
        """Test loading from non-existent queue file."""
        items = queue_service.load_queue("nonexistent_profile")
        assert items == []

    def test_load_queue_wrapper_format(self, queue_service, temp_queues_dir):
        """Test loading queue in wrapper format {items: [...]}."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        queue_data = {
            "items": [
                {
                    "id": "ulid1",
                    "url": "https://jobs.lever.co/company/job1",
                    "company": "Company",
                    "title": "Engineer",
                    "status": "SUBMITTED",
                }
            ]
        }

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        items = queue_service.load_queue(profile_id)
        assert len(items) == 1
        assert items[0].company == "Company"

    def test_load_queue_raw_array_format(self, queue_service, temp_queues_dir):
        """Test loading queue in raw array format [...]."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        queue_data = [
            {
                "id": "ulid1",
                "url": "https://jobs.lever.co/company/job1",
                "company": "Company",
                "title": "Engineer",
                "status": "SUBMITTED",
            }
        ]

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        items = queue_service.load_queue(profile_id)
        assert len(items) == 1
        assert items[0].company == "Company"

    def test_load_queue_skips_invalid_items(self, queue_service, temp_queues_dir):
        """Test that completely invalid items are skipped."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        queue_data = {
            "items": [
                {
                    "id": "ulid1",
                    "url": "https://jobs.lever.co/company/job1",
                    "company": "Company A",
                    "title": "Engineer",
                    "status": "SUBMITTED",
                },
                {
                    # Missing required fields
                    "company": "Company B",
                    "status": "SUBMITTED",
                },
                {
                    "id": "ulid3",
                    "url": "https://jobs.lever.co/company/job3",
                    "company": "Company C",
                    "title": "Designer",
                    "status": "FAILED",
                },
            ]
        }

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        items = queue_service.load_queue(profile_id)
        # Should skip the second item and load the others
        assert len(items) == 2
        assert items[0].company == "Company A"
        assert items[1].company == "Company C"

    def test_load_queue_all_statuses(self, queue_service, temp_queues_dir):
        """Test loading queue with all valid status values."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        statuses = [
            ("new", ApplicationStatus.NEW),
            ("in_progress", ApplicationStatus.IN_PROGRESS),
            ("submitted", ApplicationStatus.SUBMITTED),
            ("failed", ApplicationStatus.FAILED),
            ("captcha_blocked", ApplicationStatus.CAPTCHA_BLOCKED),
        ]

        items_data = [
            {
                "id": f"ulid{i}",
                "url": f"https://jobs.lever.co/company/job{i}",
                "company": f"Company {i}",
                "title": f"Position {i}",
                "status": status_value,
            }
            for i, (status_value, _) in enumerate(statuses)
        ]

        queue_data = {"items": items_data}

        with open(queue_path, "w") as f:
            json.dump(queue_data, f)

        items = queue_service.load_queue(profile_id)
        assert len(items) == len(statuses)

        for i, (_, expected_status) in enumerate(statuses):
            assert items[i].status == expected_status


class TestQueueServiceSaveQueue:
    """Tests for QueueService.save_queue()."""

    def test_save_queue_uses_wrapper_format(self, queue_service, temp_queues_dir):
        """Test that saved queue files use wrapper format."""
        profile_id = "test_profile"
        queue_path = Path(temp_queues_dir) / f"{profile_id}.json"

        items = [
            ApplicationItem(
                id="ulid1",
                url="https://jobs.lever.co/company/job1",
                company="Company A",
                title="Engineer",
                status=ApplicationStatus.SUBMITTED,
            )
        ]

        queue_service.save_queue(profile_id, items)

        # Verify the saved format
        with open(queue_path, "r") as f:
            data = json.load(f)

        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1
        assert data["items"][0]["company"] == "Company A"

    def test_save_and_load_roundtrip(self, queue_service, temp_queues_dir):
        """Test that saved queue can be loaded back correctly."""
        profile_id = "test_profile"

        original_items = [
            ApplicationItem(
                id="ulid1",
                url="https://jobs.lever.co/company/job1",
                company="Company A",
                title="Engineer",
                status=ApplicationStatus.NEW,
            ),
            ApplicationItem(
                id="ulid2",
                url="https://jobs.lever.co/company/job2",
                company="Company B",
                title="Designer",
                status=ApplicationStatus.SUBMITTED,
            ),
        ]

        queue_service.save_queue(profile_id, original_items)
        loaded_items = queue_service.load_queue(profile_id)

        assert len(loaded_items) == len(original_items)
        for orig, loaded in zip(original_items, loaded_items):
            assert orig.id == loaded.id
            assert orig.company == loaded.company
            assert orig.status == loaded.status
