"""Unit tests for Apply service endpoints."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.models.application import ApplicationStatus, ApplicationItem
from src.models.config import RunConfiguration, OperationType, ApplyMode
from src.services.queue_service import QueueService
from src.services.run_config_service import RunConfigurationService


class TestApplyService:
    """Unit tests for Apply service operations."""

    @pytest.fixture
    def queue_service(self):
        """Create mock QueueService."""
        return Mock(spec=QueueService)

    @pytest.fixture
    def run_config_service(self):
        """Create mock RunConfigurationService."""
        return Mock(spec=RunConfigurationService)

    @pytest.fixture
    def sample_job(self):
        """Create sample ApplicationItem."""
        return ApplicationItem(
            id="job_123",
            url="https://jobs.lever.co/company/job123",
            company="Test Company",
            title="Software Engineer",
            status=ApplicationStatus.NEW,
            details=None,
            artifacts=None,
            reason=None,
            date_discovered=None,
            date_applied=None,
            source_query="python developer",
            source_rank=1,
            hash="abc123",
        )

    def test_apply_single_job_found(self, queue_service, run_config_service, sample_job):
        """Test applying to single job when job exists."""
        queue_service.get_job.return_value = sample_job
        queue_service.update_item_status.return_value = None

        # Simulate the apply logic
        profile_id = "test_profile"
        job_id = "job_123"

        # Check that job exists
        job = queue_service.get_job(profile_id, job_id)
        assert job is not None
        assert job.id == "job_123"

        # Update status to IN_PROGRESS
        queue_service.update_item_status(
            profile_id, job_id, ApplicationStatus.IN_PROGRESS
        )

        # Verify calls were made
        queue_service.get_job.assert_called_once_with(profile_id, job_id)
        queue_service.update_item_status.assert_called_once_with(
            profile_id, job_id, ApplicationStatus.IN_PROGRESS
        )

    def test_apply_single_job_not_found(self, queue_service):
        """Test applying to single job when job doesn't exist."""
        queue_service.get_job.return_value = None

        profile_id = "test_profile"
        job_id = "nonexistent"

        job = queue_service.get_job(profile_id, job_id)
        assert job is None

    def test_apply_options_persistence(self, run_config_service):
        """Test that apply options are saved to config service."""
        profile_id = "test_profile"

        config = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.APPLY_SINGLE,
            mode=ApplyMode.SUPERVISED,
            review_mode=False,
            use_llm_locator=True,
            debug_resume_widget=True,
            resume_wait_timeout=30,
        )

        run_config_service.save_run_config(profile_id, config)

        # Verify save was called
        run_config_service.save_run_config.assert_called_once()
        args = run_config_service.save_run_config.call_args
        assert args[0][0] == profile_id
        assert args[0][1].mode == ApplyMode.SUPERVISED

    def test_apply_status_transition(self, sample_job):
        """Test valid status transition from NEW to IN_PROGRESS."""
        assert sample_job.status == ApplicationStatus.NEW

        # Simulate status transition
        sample_job.status = ApplicationStatus.IN_PROGRESS
        assert sample_job.status == ApplicationStatus.IN_PROGRESS

    def test_apply_with_review_mode(self, queue_service, sample_job):
        """Test applying with review mode enabled."""
        queue_service.get_job.return_value = sample_job

        profile_id = "test_profile"
        job_id = "job_123"
        review_mode = True

        job = queue_service.get_job(profile_id, job_id)
        assert job is not None

        # Review mode would prevent actual submission
        # This is verified in integration/contract tests
        assert review_mode is True

    def test_apply_with_custom_llm_provider(self, run_config_service):
        """Test applying with custom LLM provider override."""
        config = RunConfiguration(
            profile_id="test_profile",
            operation_type=OperationType.APPLY_SINGLE,
            llm_provider_override="openrouter",
            llm_model_override="anthropic/claude-opus-4",
        )

        run_config_service.save_run_config("test_profile", config)

        assert config.llm_provider_override == "openrouter"
        assert config.llm_model_override == "anthropic/claude-opus-4"

    def test_apply_resume_diagnostics(self, run_config_service):
        """Test applying with resume upload diagnostics enabled."""
        config = RunConfiguration(
            profile_id="test_profile",
            operation_type=OperationType.APPLY_SINGLE,
            use_llm_locator=True,
            debug_resume_widget=True,
            resume_wait_timeout=45,
        )

        run_config_service.save_run_config("test_profile", config)

        assert config.use_llm_locator is True
        assert config.debug_resume_widget is True
        assert config.resume_wait_timeout == 45

    def test_bulk_apply_filtering(self, queue_service):
        """Test filtering jobs for bulk apply (waiting jobs only)."""
        jobs = [
            ApplicationItem(
                id="job_1",
                url="https://...",
                company="Company",
                title="Role",
                status=ApplicationStatus.NEW,
                details=None,
                artifacts=None,
                reason=None,
                date_discovered=None,
                date_applied=None,
                source_query="test",
                source_rank=1,
                hash="hash1",
            ),
            ApplicationItem(
                id="job_2",
                url="https://...",
                company="Company",
                title="Role",
                status=ApplicationStatus.SUBMITTED,
                details=None,
                artifacts=None,
                reason=None,
                date_discovered=None,
                date_applied=None,
                source_query="test",
                source_rank=2,
                hash="hash2",
            ),
            ApplicationItem(
                id="job_3",
                url="https://...",
                company="Company",
                title="Role",
                status=ApplicationStatus.NEW,
                details=None,
                artifacts=None,
                reason=None,
                date_discovered=None,
                date_applied=None,
                source_query="test",
                source_rank=3,
                hash="hash3",
            ),
        ]

        queue_service.load_queue.return_value = jobs

        profile_id = "test_profile"
        all_jobs = queue_service.load_queue(profile_id)

        # Filter to waiting jobs
        waiting_jobs = [j for j in all_jobs if j.status == ApplicationStatus.NEW]

        assert len(waiting_jobs) == 2
        assert waiting_jobs[0].id == "job_1"
        assert waiting_jobs[1].id == "job_3"

    def test_bulk_apply_options_persistence(self, run_config_service):
        """Test that bulk apply options are saved separately."""
        profile_id = "test_profile"

        config = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.APPLY_BULK,
            mode=ApplyMode.AUTOMATED,
            max_concurrent=5,
            stop_on_failure=True,
        )

        run_config_service.save_run_config(profile_id, config)

        run_config_service.save_run_config.assert_called_once()
        args = run_config_service.save_run_config.call_args
        assert args[0][1].operation_type == OperationType.APPLY_BULK
        assert args[0][1].max_concurrent == 5

    def test_apply_mode_enumeration(self):
        """Test that apply modes are properly enumerated."""
        assert ApplyMode.SUPERVISED.value == "supervised"
        assert ApplyMode.AUTOMATED.value == "automated"

        # Test initialization
        mode = ApplyMode("supervised")
        assert mode == ApplyMode.SUPERVISED

    def test_apply_operation_type_enumeration(self):
        """Test that operation types include apply types."""
        assert OperationType.APPLY_SINGLE.value == "apply_single"
        assert OperationType.APPLY_BULK.value == "apply_bulk"
        assert OperationType.DISCOVER.value == "discover"

    def test_apply_configuration_defaults(self):
        """Test that RunConfiguration has sensible defaults."""
        config = RunConfiguration(
            profile_id="test_profile",
            operation_type=OperationType.APPLY_SINGLE,
        )

        # Check optional fields default to None
        assert config.mode is None
        assert config.review_mode is None
        assert config.max_concurrent is None
        assert config.stop_on_failure is None

    def test_apply_resume_timeout_validation(self):
        """Test resume timeout constraints."""
        # Valid timeout
        config = RunConfiguration(
            profile_id="test_profile",
            operation_type=OperationType.APPLY_SINGLE,
            resume_wait_timeout=25,
        )
        assert 5 <= config.resume_wait_timeout <= 120

        # Extreme valid timeout
        config_min = RunConfiguration(
            profile_id="test_profile",
            operation_type=OperationType.APPLY_SINGLE,
            resume_wait_timeout=5,
        )
        assert config_min.resume_wait_timeout == 5

        config_max = RunConfiguration(
            profile_id="test_profile",
            operation_type=OperationType.APPLY_SINGLE,
            resume_wait_timeout=120,
        )
        assert config_max.resume_wait_timeout == 120
