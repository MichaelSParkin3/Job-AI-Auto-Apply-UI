"""Apply API endpoints for single and bulk job application workflows."""

from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException

from src.models.config import (
    RunConfiguration,
    OperationType,
    ApplyMode as ApplyModeEnum,
)
from src.models.application import ApplicationStatus
from src.services.cli_service import CLIService
from src.services.queue_service import QueueService
from src.services.run_config_service import RunConfigurationService

router = APIRouter(prefix="/apply", tags=["apply"])

# Service instances (would normally be injected)
cli_service = CLIService()
queue_service = QueueService()
run_config_service = RunConfigurationService()


@router.post("/single", response_model=Dict[str, Any])
async def apply_single(
    profile_id: str,
    job_id: str,
    mode: Optional[str] = "supervised",
    review_mode: Optional[bool] = False,
    llm_provider_override: Optional[str] = None,
    llm_model_override: Optional[str] = None,
    use_llm_locator: Optional[bool] = False,
    debug_resume_widget: Optional[bool] = False,
    resume_wait_timeout: Optional[int] = 25,
    audit_after_submit: Optional[bool] = False,
    save_logs: Optional[bool] = False,
    logs_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply to a single job.

    Args:
        profile_id: Profile ID to apply with
        job_id: Job ID to apply to
        mode: supervised or automated
        review_mode: Review form before submit
        llm_provider_override: LLM provider override
        llm_model_override: LLM model override
        use_llm_locator: Use LLM for element finding
        debug_resume_widget: Debug resume upload widget
        resume_wait_timeout: Resume upload timeout in seconds
        audit_after_submit: Audit page after submit
        save_logs: Save execution logs
        logs_dir: Directory to save logs

    Returns:
        Dict with job_id, status, and streaming log info

    Raises:
        HTTPException: If job not found or apply fails
    """
    try:
        # Validate job exists
        job = queue_service.get_job(profile_id, job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        # Update job status to IN_PROGRESS
        queue_service.update_item_status(
            profile_id,
            job_id,
            ApplicationStatus.IN_PROGRESS
        )

        # Save the options for next time
        config = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.APPLY_SINGLE,
            mode=ApplyModeEnum(mode) if mode else ApplyModeEnum.SUPERVISED,
            review_mode=review_mode,
            llm_provider_override=llm_provider_override,
            llm_model_override=llm_model_override,
            use_llm_locator=use_llm_locator,
            debug_resume_widget=debug_resume_widget,
            resume_wait_timeout=resume_wait_timeout,
            audit_after_submit=audit_after_submit,
            save_logs=save_logs,
            logs_dir=logs_dir,
        )
        run_config_service.save_run_config(profile_id, config)

        # Execute apply via CLI (simplified - real implementation streams)
        return {
            "status": "started",
            "profile_id": profile_id,
            "job_id": job_id,
            "mode": mode,
            "message": "Application execution initiated",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=Dict[str, Any])
async def apply_bulk(
    profile_id: str,
    mode: Optional[str] = "supervised",
    review_mode: Optional[bool] = False,
    max_concurrent: Optional[int] = 3,
    stop_on_failure: Optional[bool] = False,
    llm_provider_override: Optional[str] = None,
    llm_model_override: Optional[str] = None,
    save_logs: Optional[bool] = False,
    logs_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply to multiple waiting jobs.

    Args:
        profile_id: Profile ID to apply with
        mode: supervised or automated
        review_mode: Review form before submit
        max_concurrent: Max concurrent applications
        stop_on_failure: Stop on first failure
        llm_provider_override: LLM provider override
        llm_model_override: LLM model override
        save_logs: Save execution logs
        logs_dir: Directory to save logs

    Returns:
        Dict with total jobs and streaming progress info

    Raises:
        HTTPException: If profile not found or apply fails
    """
    try:
        # Load queue for profile
        items = queue_service.load_queue(profile_id)

        # Filter to waiting jobs
        waiting_jobs = [
            item for item in items
            if item.status == ApplicationStatus.NEW
        ]

        if not waiting_jobs:
            return {
                "status": "no_jobs",
                "profile_id": profile_id,
                "total_jobs": 0,
                "message": "No waiting jobs to apply to",
            }

        # Save the options for next time
        config = RunConfiguration(
            profile_id=profile_id,
            operation_type=OperationType.APPLY_BULK,
            mode=ApplyModeEnum(mode) if mode else ApplyModeEnum.SUPERVISED,
            review_mode=review_mode,
            max_concurrent=max_concurrent,
            stop_on_failure=stop_on_failure,
            llm_provider_override=llm_provider_override,
            llm_model_override=llm_model_override,
            save_logs=save_logs,
            logs_dir=logs_dir,
        )
        run_config_service.save_run_config(profile_id, config)

        # Update all waiting jobs to IN_PROGRESS
        for item in waiting_jobs:
            queue_service.update_item_status(
                profile_id,
                item.id,
                ApplicationStatus.IN_PROGRESS
            )

        # Execute bulk apply via CLI (simplified - real implementation streams)
        return {
            "status": "started",
            "profile_id": profile_id,
            "total_jobs": len(waiting_jobs),
            "mode": mode,
            "max_concurrent": max_concurrent,
            "message": f"Bulk application initiated for {len(waiting_jobs)} jobs",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}", response_model=Dict[str, Any])
async def get_apply_status(
    job_id: str,
    profile_id: str,
) -> Dict[str, Any]:
    """Get current application status for a job.

    Args:
        job_id: Job ID to check status
        profile_id: Profile ID

    Returns:
        Current status with metadata

    Raises:
        HTTPException: If job not found
    """
    try:
        job = queue_service.get_job(profile_id, job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        response = {
            "job_id": job_id,
            "status": job.status.value,
            "company": job.company,
            "title": job.title,
        }

        # Add confirmation details if submitted
        if job.status == ApplicationStatus.SUBMITTED and job.artifacts:
            response["confirmation_id"] = job.artifacts.confirmation_id
            response["confirmation_text"] = job.artifacts.confirmation_text
            response["submitted_at"] = job.date_applied

        # Add failure reason if failed
        if job.status == ApplicationStatus.FAILED and job.reason:
            response["error_code"] = job.reason.code
            response["error_message"] = job.reason.message

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/{job_id}", response_model=Dict[str, Any])
async def get_apply_logs(
    job_id: str,
    profile_id: str,
) -> Dict[str, Any]:
    """Get application logs for a job.

    Note: This is a simplified implementation. In production,
    you would stream logs using SSE or return log file contents.

    Args:
        job_id: Job ID to get logs for
        profile_id: Profile ID

    Returns:
        Logs array or empty if no logs available
    """
    try:
        job = queue_service.get_job(profile_id, job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        # Simplified: return empty logs
        # Real implementation would:
        # - Read log files from artifacts directory
        # - OR stream logs from background task
        return {
            "job_id": job_id,
            "logs": [],
            "message": "No logs available",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/last-options/{profile_id}", response_model=Dict[str, Any])
async def get_last_apply_options(profile_id: str) -> Dict[str, Any]:
    """Get last-used apply options for a profile.

    Args:
        profile_id: Profile ID

    Returns:
        Last-used options for both single and bulk apply

    Raises:
        HTTPException: If loading fails
    """
    try:
        # Try to load single apply config
        single_config = run_config_service.load_run_config(
            profile_id,
            OperationType.APPLY_SINGLE
        )

        # Try to load bulk apply config
        bulk_config = run_config_service.load_run_config(
            profile_id,
            OperationType.APPLY_BULK
        )

        return {
            "profile_id": profile_id,
            "single_apply": {
                "mode": single_config.mode or "supervised",
                "review_mode": single_config.review_mode or False,
                "use_llm_locator": single_config.use_llm_locator or False,
                "debug_resume_widget": single_config.debug_resume_widget or False,
                "resume_wait_timeout": single_config.resume_wait_timeout or 25,
                "audit_after_submit": single_config.audit_after_submit or False,
                "save_logs": single_config.save_logs or False,
            },
            "bulk_apply": {
                "mode": bulk_config.mode or "supervised",
                "review_mode": bulk_config.review_mode or False,
                "max_concurrent": bulk_config.max_concurrent or 3,
                "stop_on_failure": bulk_config.stop_on_failure or False,
                "save_logs": bulk_config.save_logs or False,
            },
        }

    except Exception:
        # Return defaults if unable to load
        return {
            "profile_id": profile_id,
            "single_apply": {
                "mode": "supervised",
                "review_mode": False,
                "use_llm_locator": False,
                "debug_resume_widget": False,
                "resume_wait_timeout": 25,
                "audit_after_submit": False,
                "save_logs": False,
            },
            "bulk_apply": {
                "mode": "supervised",
                "review_mode": False,
                "max_concurrent": 3,
                "stop_on_failure": False,
                "save_logs": False,
            },
        }
