"""Unit tests for ApplicationQueue serialization behaviors."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.application_queue import (
    ApplicationItem,
    ApplicationQueue,
    ApplicationStatus,
    Artifacts,
    Reason,
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


def test_application_item_to_dict_emits_enum_strings(sample_item: ApplicationItem) -> None:
    """Enum fields and reason objects should round-trip as JSON-friendly values."""

    sample_item.status = ApplicationStatus.CAPTCHA_BLOCKED
    sample_item.reason = Reason(code="captcha", message="Blocked by hCaptcha")

    payload = sample_item.to_dict()
    assert payload["status"] == "captcha_blocked"
    assert payload["details"] is None
    assert payload["reason"] == {"code": "captcha", "message": "Blocked by hCaptcha"}

    round_tripped = json.loads(json.dumps(payload, ensure_ascii=False))
    assert round_tripped["status"] == "captcha_blocked"
    assert round_tripped["details"] is None
    assert round_tripped["reason"]["code"] == "captcha"


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


def test_queue_status_transitions_persist_to_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
) -> None:
    """Status transitions should persist with `details` staying null and artifacts intact."""

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
    )
    queue = ApplicationQueue("profile-queue", base_dir=tmp_path)
    queue.enqueue([sample_item])

    queue.resume(sample_item.id)
    queue.mark_submitted(
        sample_item.id,
        Artifacts(confirmation_text="Submitted", confirmation_id="CONF-123"),
    )

    # Ensure JSON payload reflects the updated status and null details
    persisted = json.loads(queue._path.read_text(encoding="utf-8"))
    entry = persisted["items"][0]
    assert entry["status"] == "submitted"
    assert entry["details"] is None
    assert entry["artifacts"]["confirmation_id"] == "CONF-123"

    # Reload queue to confirm enums and null fields survive round-trip
    reloaded = ApplicationQueue("profile-queue", base_dir=tmp_path)
    stored = reloaded.get(sample_item.id)
    assert stored is not None
    assert stored.status is ApplicationStatus.SUBMITTED
    assert stored.details is None
    assert stored.artifacts.confirmation_id == "CONF-123"
