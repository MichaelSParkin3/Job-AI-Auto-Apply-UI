"""Unit tests for ApplicationQueue status transitions and artifact serialization."""

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
    """Create a sample application item for testing."""
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


class TestPendingReviewTransitions:
    """Test PENDING_REVIEW status transitions."""

    def test_in_progress_to_pending_review_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """IN_PROGRESS → PENDING_REVIEW should be valid."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)

        # Should succeed without raising
        artifacts = Artifacts(
            form_state_path="/path/to/pre.json",
            screenshot_before_path="/path/to/pre-full.jpg",
        )
        queue.mark_pending_review(sample_item.id, artifacts)

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.PENDING_REVIEW
        assert item.artifacts.form_state_path == "/path/to/pre.json"
        assert item.artifacts.screenshot_before_path == "/path/to/pre-full.jpg"

    def test_pending_review_to_in_progress_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """PENDING_REVIEW → IN_PROGRESS (via resume) should be valid."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)
        queue.mark_pending_review(
            sample_item.id,
            Artifacts(form_state_path="/path/to/pre.json"),
        )

        # Resume from PENDING_REVIEW
        queue.resume(sample_item.id)

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.IN_PROGRESS

    def test_pending_review_to_submitted_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """PENDING_REVIEW → SUBMITTED should be valid."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)
        queue.mark_pending_review(
            sample_item.id,
            Artifacts(form_state_path="/path/to/pre.json"),
        )

        # Mark as submitted from PENDING_REVIEW
        queue.mark_submitted(
            sample_item.id,
            Artifacts(confirmation_text="Submitted", confirmation_id="CONF-123"),
        )

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.SUBMITTED

    def test_pending_review_to_failed_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """PENDING_REVIEW → FAILED should be valid."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)
        queue.mark_pending_review(
            sample_item.id,
            Artifacts(form_state_path="/path/to/pre.json"),
        )

        # Mark as failed from PENDING_REVIEW
        queue.mark_failed(
            sample_item.id,
            Reason(code="error", message="Failed after review"),
        )

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.FAILED

    def test_new_to_pending_review_is_invalid(self, sample_item: ApplicationItem) -> None:
        """NEW → PENDING_REVIEW should raise ValueError."""
        sample_item.status = ApplicationStatus.NEW

        with pytest.raises(ValueError, match="Invalid status transition"):
            sample_item.update_status(ApplicationStatus.PENDING_REVIEW)


class TestCaptchaBlockedTransitions:
    """Test CAPTCHA_BLOCKED status transitions."""

    def test_in_progress_to_captcha_blocked_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """IN_PROGRESS → CAPTCHA_BLOCKED should be valid."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)

        # Mark as captcha blocked
        artifacts = Artifacts(
            form_state_path="/path/to/pre.json",
            screenshot_before_path="/path/to/pre-full.jpg",
        )
        queue.mark_captcha(
            sample_item.id,
            Reason(code="captcha_blocked", message="hCaptcha detected"),
            artifacts,
        )

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.CAPTCHA_BLOCKED
        assert item.reason is not None
        assert item.reason.code == "captcha_blocked"
        assert item.artifacts.form_state_path == "/path/to/pre.json"

    def test_captcha_blocked_to_in_progress_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """CAPTCHA_BLOCKED → IN_PROGRESS (via resume) should be valid."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)
        queue.mark_captcha(
            sample_item.id,
            Reason(code="captcha_blocked", message="hCaptcha detected"),
        )

        # Resume from CAPTCHA_BLOCKED
        queue.resume(sample_item.id)

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.IN_PROGRESS

    def test_captcha_blocked_to_failed_is_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """CAPTCHA_BLOCKED → FAILED should be valid."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)
        queue.mark_captcha(
            sample_item.id,
            Reason(code="captcha_blocked", message="hCaptcha detected"),
        )

        # Mark as failed from CAPTCHA_BLOCKED
        queue.mark_failed(
            sample_item.id,
            Reason(code="error", message="Failed after captcha"),
        )

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.FAILED


class TestArtifactFieldSerialization:
    """Test that new artifact fields serialize and deserialize correctly."""

    def test_form_state_path_serialization(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """form_state_path should round-trip through JSON."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)

        artifacts = Artifacts(form_state_path="/path/to/pre.json")
        queue.mark_pending_review(sample_item.id, artifacts)

        # Reload queue and verify
        reloaded = ApplicationQueue("profile-test", base_dir=tmp_path)
        item = reloaded.get(sample_item.id)
        assert item is not None
        assert item.artifacts.form_state_path == "/path/to/pre.json"

    def test_screenshot_before_path_serialization(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """screenshot_before_path should round-trip through JSON."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)

        artifacts = Artifacts(screenshot_before_path="/path/to/pre-full.jpg")
        queue.mark_pending_review(sample_item.id, artifacts)

        # Reload queue and verify
        reloaded = ApplicationQueue("profile-test", base_dir=tmp_path)
        item = reloaded.get(sample_item.id)
        assert item is not None
        assert item.artifacts.screenshot_before_path == "/path/to/pre-full.jpg"

    def test_screenshot_after_path_serialization(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """screenshot_after_path should round-trip through JSON."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])
        queue.resume(sample_item.id)

        artifacts = Artifacts(
            confirmation_text="Submitted",
            confirmation_id="CONF-123",
            screenshot_after_path="/path/to/post-full.jpg",
        )
        queue.mark_submitted(sample_item.id, artifacts)

        # Reload queue and verify
        reloaded = ApplicationQueue("profile-test", base_dir=tmp_path)
        item = reloaded.get(sample_item.id)
        assert item is not None
        assert item.artifacts.screenshot_after_path == "/path/to/post-full.jpg"

    def test_all_new_artifact_fields_together(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """All three new artifact fields should serialize together."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])

        sample_item.artifacts = Artifacts(
            form_state_path="/path/to/pre.json",
            screenshot_before_path="/path/to/pre-full.jpg",
            screenshot_after_path="/path/to/post-full.jpg",
            confirmation_text="Submitted",
            confirmation_id="CONF-123",
        )
        queue.update(sample_item)

        # Verify JSON payload
        persisted = json.loads(queue._path.read_text(encoding="utf-8"))
        entry = persisted["items"][0]
        assert entry["artifacts"]["form_state_path"] == "/path/to/pre.json"
        assert entry["artifacts"]["screenshot_before_path"] == "/path/to/pre-full.jpg"
        assert entry["artifacts"]["screenshot_after_path"] == "/path/to/post-full.jpg"

        # Reload and verify
        reloaded = ApplicationQueue("profile-test", base_dir=tmp_path)
        item = reloaded.get(sample_item.id)
        assert item is not None
        assert item.artifacts.form_state_path == "/path/to/pre.json"
        assert item.artifacts.screenshot_before_path == "/path/to/pre-full.jpg"
        assert item.artifacts.screenshot_after_path == "/path/to/post-full.jpg"


class TestManualStatusOverrides:
    """Test skip_validation parameter for manual UI status changes."""

    def test_skip_validation_false_enforces_strict_validation(self, sample_item: ApplicationItem) -> None:
        """With skip_validation=False (default), invalid transitions should raise."""
        sample_item.status = ApplicationStatus.SKIPPED

        # SKIPPED → CAPTCHA_BLOCKED is normally invalid
        with pytest.raises(ValueError, match="Invalid status transition"):
            sample_item.update_status(ApplicationStatus.CAPTCHA_BLOCKED, skip_validation=False)

    def test_skip_validation_true_allows_any_transition(self, sample_item: ApplicationItem) -> None:
        """With skip_validation=True, any transition should succeed."""
        sample_item.status = ApplicationStatus.SKIPPED

        # SKIPPED → CAPTCHA_BLOCKED should now succeed
        sample_item.update_status(ApplicationStatus.CAPTCHA_BLOCKED, skip_validation=True)
        assert sample_item.status == ApplicationStatus.CAPTCHA_BLOCKED

    def test_skip_validation_default_is_false(self, sample_item: ApplicationItem) -> None:
        """Default behavior (no skip_validation param) should enforce validation."""
        sample_item.status = ApplicationStatus.SKIPPED

        # Should fail because default is skip_validation=False
        with pytest.raises(ValueError, match="Invalid status transition"):
            sample_item.update_status(ApplicationStatus.CAPTCHA_BLOCKED)

    def test_skip_validation_with_reason(self, sample_item: ApplicationItem) -> None:
        """skip_validation=True should work with reason parameter."""
        sample_item.status = ApplicationStatus.SUBMITTED
        reason = Reason(code="manual_update", message="User corrected status")

        # SUBMITTED → NEW is invalid but skip_validation allows it
        sample_item.update_status(ApplicationStatus.NEW, reason=reason, skip_validation=True)
        assert sample_item.status == ApplicationStatus.NEW
        assert sample_item.reason == reason

    def test_all_invalid_transitions_work_with_skip_validation(self, sample_item: ApplicationItem) -> None:
        """Various invalid transitions should work with skip_validation=True."""
        invalid_transitions = [
            (ApplicationStatus.SUBMITTED, ApplicationStatus.NEW),
            (ApplicationStatus.FAILED, ApplicationStatus.PENDING_REVIEW),
            (ApplicationStatus.CAPTCHA_BLOCKED, ApplicationStatus.SUBMITTED),
            (ApplicationStatus.SKIPPED, ApplicationStatus.IN_PROGRESS),
        ]

        for from_status, to_status in invalid_transitions:
            sample_item.status = from_status
            # Should not raise
            sample_item.update_status(to_status, skip_validation=True)
            assert sample_item.status == to_status

    def test_queue_methods_still_use_strict_validation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_item: ApplicationItem
    ) -> None:
        """Queue methods like mark_submitted should still enforce validation."""
        monkeypatch.setattr(
            "job_ai_auto_apply_ui.application_queue.log_event", lambda *args, **kwargs: None
        )
        queue = ApplicationQueue("profile-test", base_dir=tmp_path)
        queue.enqueue([sample_item])

        # Set item to IN_PROGRESS first
        queue.resume(sample_item.id)

        # Now mark as submitted - this should succeed because IN_PROGRESS → SUBMITTED is valid
        artifacts = Artifacts(confirmation_text="OK", confirmation_id="CONF-123")
        queue.mark_submitted(sample_item.id, artifacts)

        item = queue.get(sample_item.id)
        assert item is not None
        assert item.status == ApplicationStatus.SUBMITTED

        # Verify that direct update_status still enforces validation
        # SUBMITTED → IN_PROGRESS is invalid (SUBMITTED is a terminal state)
        submitted_item = ApplicationItem(
            id="item-002",
            url="https://jobs.example.com/role2",
            company="Example Co",
            title="Engineer",
            status=ApplicationStatus.SUBMITTED,
            discovered_at=sample_item.discovered_at,
            last_updated_at=sample_item.last_updated_at,
            hash="hash-002",
            artifacts=Artifacts(),
            details=None,
            reason=None,
        )
        with pytest.raises(ValueError, match="Invalid status transition"):
            submitted_item.update_status(ApplicationStatus.IN_PROGRESS)
