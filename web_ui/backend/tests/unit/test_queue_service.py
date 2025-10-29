"""Unit tests for QueueService."""

import json
import os
import tempfile
from pathlib import Path
from typing import List

import pytest
from src.models.application import ApplicationStatus, ApplicationItem
from src.services.queue_service import QueueService


@pytest.fixture
def temp_queues_dir(tmp_path):
    """Create temporary queues directory."""
    queues_dir = tmp_path / "queues"
    queues_dir.mkdir()
    return str(queues_dir)


@pytest.fixture
def queue_service(temp_queues_dir):
    """Create QueueService with temporary directory."""
    return QueueService(queues_dir=temp_queues_dir)


@pytest.fixture
def sample_queue_data() -> List[dict]:
    """Sample queue data for testing."""
    return [
        {
            "id": "01HX1234567890ABCDEFGHJ",
            "url": "https://jobs.lever.co/company/job-1",
            "company": "TechCorp",
            "title": "Senior Software Engineer",
            "status": "NEW",
            "date_discovered": "2024-10-28T10:00:00Z",
            "hash": "abc123",
        },
        {
            "id": "01HX2234567890ABCDEFGHJ",
            "url": "https://jobs.lever.co/company/job-2",
            "company": "StartupCo",
            "title": "Frontend Developer",
            "status": "IN_PROGRESS",
            "date_discovered": "2024-10-27T15:30:00Z",
            "hash": "def456",
        },
        {
            "id": "01HX3234567890ABCDEFGHJ",
            "url": "https://jobs.lever.co/company/job-3",
            "company": "BigTech",
            "title": "Staff Engineer",
            "status": "SUBMITTED",
            "date_discovered": "2024-10-26T09:15:00Z",
            "date_applied": "2024-10-27T14:20:00Z",
            "hash": "ghi789",
        },
    ]


@pytest.fixture
def profile_with_queue(temp_queues_dir, sample_queue_data):
    """Create a profile with existing queue file."""
    profile_id = "test_profile"
    queue_file = Path(temp_queues_dir) / f"{profile_id}.json"
    queue_file.write_text(json.dumps(sample_queue_data), encoding="utf-8")
    return profile_id


def test_load_queue_empty(queue_service):
    """Test loading queue for profile with no queue file."""
    items = queue_service.load_queue("nonexistent_profile")
    assert items == []


def test_load_queue_existing(queue_service, profile_with_queue, sample_queue_data):
    """Test loading existing queue."""
    items = queue_service.load_queue(profile_with_queue)
    assert len(items) == len(sample_queue_data)
    assert items[0].id == sample_queue_data[0]["id"]
    assert items[0].company == sample_queue_data[0]["company"]
    assert items[0].status == ApplicationStatus.NEW


def test_save_queue(queue_service, temp_queues_dir, sample_queue_data):
    """Test saving queue to file."""
    profile_id = "test_save"
    items = [ApplicationItem(**item) for item in sample_queue_data]

    queue_service.save_queue(profile_id, items)

    # Verify file exists
    queue_file = Path(temp_queues_dir) / f"{profile_id}.json"
    assert queue_file.exists()

    # Verify content
    loaded = queue_service.load_queue(profile_id)
    assert len(loaded) == len(items)
    assert loaded[0].id == items[0].id


def test_enqueue_job_new(queue_service):
    """Test enqueueing a new job."""
    profile_id = "test_enqueue"
    item = ApplicationItem(
        id="01HX4234567890ABCDEFGHJ",
        url="https://jobs.lever.co/company/new-job",
        company="NewCo",
        title="DevOps Engineer",
        status=ApplicationStatus.NEW,
    )

    result = queue_service.enqueue_job(profile_id, item)

    assert result.id == item.id
    assert result.hash is not None

    # Verify it was added to queue
    queue = queue_service.load_queue(profile_id)
    assert len(queue) == 1
    assert queue[0].id == item.id


def test_enqueue_job_duplicate(queue_service, profile_with_queue):
    """Test enqueueing a duplicate job (same hash)."""
    # Load existing queue
    existing = queue_service.load_queue(profile_with_queue)
    original_count = len(existing)

    # Try to enqueue duplicate
    duplicate = ApplicationItem(
        id="01HX9999999999ABCDEFGHJ",  # Different ID
        url=existing[0].url,  # Same URL
        company=existing[0].company,  # Same company
        title=existing[0].title,  # Same title
        status=ApplicationStatus.NEW,
    )

    result = queue_service.enqueue_job(profile_with_queue, duplicate)

    # Should return existing item, not add duplicate
    assert result.id == existing[0].id

    # Queue size should not increase
    queue = queue_service.load_queue(profile_with_queue)
    assert len(queue) == original_count


def test_get_job_exists(queue_service, profile_with_queue, sample_queue_data):
    """Test getting a specific job by ID."""
    job_id = sample_queue_data[0]["id"]
    item = queue_service.get_job(profile_with_queue, job_id)

    assert item is not None
    assert item.id == job_id
    assert item.company == sample_queue_data[0]["company"]


def test_get_job_not_found(queue_service, profile_with_queue):
    """Test getting a non-existent job."""
    item = queue_service.get_job(profile_with_queue, "nonexistent_id")
    assert item is None


def test_update_item_status(queue_service, profile_with_queue, sample_queue_data):
    """Test updating job status."""
    job_id = sample_queue_data[0]["id"]

    updated = queue_service.update_item_status(
        profile_with_queue, job_id, ApplicationStatus.IN_PROGRESS
    )

    assert updated.status == ApplicationStatus.IN_PROGRESS

    # Verify persistence
    item = queue_service.get_job(profile_with_queue, job_id)
    assert item.status == ApplicationStatus.IN_PROGRESS


def test_remove_item(queue_service, profile_with_queue, sample_queue_data):
    """Test removing a job from queue."""
    job_id = sample_queue_data[0]["id"]
    original_count = len(sample_queue_data)

    queue_service.remove_item(profile_with_queue, job_id)

    # Verify removed
    queue = queue_service.load_queue(profile_with_queue)
    assert len(queue) == original_count - 1
    assert all(item.id != job_id for item in queue)


def test_get_status_counts(queue_service, profile_with_queue):
    """Test getting status counts."""
    counts = queue_service.get_status_counts(profile_with_queue)

    assert counts["NEW"] == 1
    assert counts["IN_PROGRESS"] == 1
    assert counts["SUBMITTED"] == 1
    assert counts["FAILED"] == 0
    assert counts["CAPTCHA_BLOCKED"] == 0


def test_compute_hash_consistency(queue_service):
    """Test hash computation is consistent."""
    hash1 = queue_service._compute_hash(
        "https://jobs.lever.co/test", "Company", "Job Title"
    )
    hash2 = queue_service._compute_hash(
        "https://jobs.lever.co/test", "Company", "Job Title"
    )

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


def test_compute_hash_different(queue_service):
    """Test different inputs produce different hashes."""
    hash1 = queue_service._compute_hash(
        "https://jobs.lever.co/test1", "Company1", "Job1"
    )
    hash2 = queue_service._compute_hash(
        "https://jobs.lever.co/test2", "Company2", "Job2"
    )

    assert hash1 != hash2


def test_utf8_bom_handling(queue_service, temp_queues_dir):
    """Test handling of UTF-8 BOM in queue files."""
    profile_id = "test_bom"
    queue_file = Path(temp_queues_dir) / f"{profile_id}.json"

    # Write JSON with BOM
    data = [
        {
            "id": "01HX5234567890ABCDEFGHJ",
            "url": "https://jobs.lever.co/company/test",
            "company": "TestCo",
            "title": "Test Job",
            "status": "NEW",
        }
    ]
    queue_file.write_text(
        "\ufeff" + json.dumps(data), encoding="utf-8-sig"
    )

    # Should load without errors
    items = queue_service.load_queue(profile_id)
    assert len(items) == 1
    assert items[0].company == "TestCo"
