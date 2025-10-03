"""Unit tests for ApplicationQueue serialization behaviors."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.application_queue import (
    ApplicationItem,
    ApplicationQueue,
    ApplicationStatus,
    Artifacts,
)


@pytest.fixture()
def sample_item() -> ApplicationItem:
    """Build an application item with optional details omitted."""

    now = datetime.now(UTC)
    return ApplicationItem(
        id="item-001",
        url="https://jobs.example.com/role",
        company="Example Co",
        title="Software Engineer",
        status=ApplicationStatus.NEW,
        discovered_at=now,
        last_updated_at=now,
        hash="hash-001",
        artifacts=Artifacts(),
        details=None,
        reason=None,
    )


def test_application_item_serializes_without_details(sample_item: ApplicationItem) -> None:
    """`details` should remain ``None`` through serialization boundaries."""

    payload = sample_item.to_dict()
    assert payload["details"] is None

    reconstructed = ApplicationItem.from_dict(payload)
    assert reconstructed.details is None
    assert reconstructed.id == sample_item.id
    assert reconstructed.company == sample_item.company


def test_queue_round_trip_preserves_missing_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
) -> None:
    """Persisting through ApplicationQueue should keep ``details`` unset."""

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
    )
    queue = ApplicationQueue("profile-queue", base_dir=tmp_path)
    queue.enqueue([sample_item])

    reloaded = ApplicationQueue("profile-queue", base_dir=tmp_path)
    stored = reloaded.get(sample_item.id)
    assert stored is not None
    assert stored.details is None
