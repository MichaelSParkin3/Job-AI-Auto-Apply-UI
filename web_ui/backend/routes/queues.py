"""Routes for job queue management and viewing."""

import structlog
from fastapi import APIRouter, HTTPException
from pathlib import Path

from job_ai_auto_apply_ui.application_queue import ApplicationQueue, ApplicationStatus
from job_ai_auto_apply_ui.profile_manager import load_profile

from ..models.queue_models import (
    QueueResponse,
    QueueGroupResponse,
    JobItemResponse,
    JobDetailsResponse,
    ArtifactsResponse,
    ReasonResponse,
    JobDetailPageResponse,
)
from ..config import web_settings

router = APIRouter()
logger = structlog.get_logger()

# Status grouping: map ApplicationStatus to friendly labels
STATUS_GROUPS = {
    "waiting": {
        "label": "Jobs Waiting",
        "status_values": [ApplicationStatus.NEW.value, ApplicationStatus.IN_PROGRESS.value],
    },
    "skipped": {
        "label": "Jobs Skipped",
        "status_values": [ApplicationStatus.FAILED.value, ApplicationStatus.SKIPPED.value],
    },
    "captcha_stopped": {
        "label": "Captcha Stopped",
        "status_values": [ApplicationStatus.CAPTCHA_BLOCKED.value],
    },
    "submitted": {
        "label": "Submitted Jobs",
        "status_values": [ApplicationStatus.SUBMITTED.value],
    },
    "pending_review": {
        "label": "Pending Review",
        "status_values": [ApplicationStatus.PENDING_REVIEW.value],
    },
}


def _item_to_response(item) -> JobItemResponse:
    """Convert ApplicationItem to JobItemResponse."""
    # Convert JobDetails to response model
    details = None
    if item.details:
        details = JobDetailsResponse(
            location=item.details.location,
            work_model=item.details.work_model,
            employment_type=item.details.employment_type,
            department=item.details.department,
            posting_date=item.details.posting_date,
            compensation=item.details.compensation,
            posting_excerpt=item.details.posting_excerpt,
            posting_text=item.details.posting_text,
            tech_tags=item.details.tech_tags,
            source_query=item.details.source_query,
            source_rank=item.details.source_rank,
            apply_url=item.details.apply_url,
            closed=item.details.closed,
            extracted_at=item.details.extracted_at,
        )

    # Convert Artifacts to response model
    artifacts = None
    if item.artifacts:
        artifacts = ArtifactsResponse(
            dom_snapshot_path=item.artifacts.dom_snapshot_path,
            screenshot_path=item.artifacts.screenshot_path,
            video_path=item.artifacts.video_path,
            har_path=item.artifacts.har_path,
            confirmation_text=item.artifacts.confirmation_text,
            confirmation_id=item.artifacts.confirmation_id,
            form_state_path=item.artifacts.form_state_path,
            screenshot_before_path=item.artifacts.screenshot_before_path,
            screenshot_after_path=item.artifacts.screenshot_after_path,
        )

    # Convert Reason to response model
    reason = None
    if item.reason:
        reason = ReasonResponse(code=item.reason.code, message=item.reason.message)

    return JobItemResponse(
        id=item.id,
        url=item.url,
        company=item.company,
        title=item.title,
        status=item.status.value,
        discovered_at=item.discovered_at,
        last_updated_at=item.last_updated_at,
        details=details,
        artifacts=artifacts,
        reason=reason,
    )


@router.get("/queues/{profile_id}", response_model=QueueResponse)
async def get_queue(profile_id: str):
    """
    Get the job queue for a profile, organized by status groups.

    Args:
        profile_id: The profile ID to fetch queue for

    Returns:
        QueueResponse with grouped jobs organized by status
    """
    try:
        # Validate profile exists
        profile = load_profile(profile_id)

        logger.info("queue.fetch", profile_id=profile_id)

        # Load queue
        queue = ApplicationQueue(profile_id)
        items = list(queue.iter_items())

        # Group items by status
        groups = []
        for group_key, group_config in STATUS_GROUPS.items():
            status_values = group_config["status_values"]
            group_items = [item for item in items if item.status.value in status_values]

            if group_items:  # Only include groups with items
                job_responses = [_item_to_response(item) for item in group_items]
                groups.append(
                    QueueGroupResponse(
                        label=group_config["label"],
                        status_values=status_values,
                        count=len(group_items),
                        items=job_responses,
                    )
                )

        return QueueResponse(
            profile_id=profile_id,
            total_count=len(items),
            groups=groups,
        )

    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=profile_id)
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    except Exception as e:
        logger.error("queue.fetch.error", profile_id=profile_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queues/{profile_id}/jobs/{job_id}", response_model=JobDetailPageResponse)
async def get_job_detail(profile_id: str, job_id: str):
    """
    Get complete details for a specific job in the queue.

    Args:
        profile_id: The profile ID
        job_id: The job application item ID (ULID)

    Returns:
        JobDetailPageResponse with full job data and answer cache
    """
    try:
        # Validate profile exists
        profile = load_profile(profile_id)

        logger.info("job.detail.fetch", profile_id=profile_id, job_id=job_id)

        # Load queue and find item
        queue = ApplicationQueue(profile_id)
        item = None
        for queued_item in queue.iter_items():
            if queued_item.id == job_id:
                item = queued_item
                break

        if not item:
            logger.warning("Job not found", profile_id=profile_id, job_id=job_id)
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

        job_response = _item_to_response(item)

        # TODO: Load answer cache when available
        # For now, return empty answer cache
        answer_cache = {}

        return JobDetailPageResponse(
            job=job_response,
            profile_id=profile_id,
            answer_cache=answer_cache,
        )

    except HTTPException:
        raise
    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=profile_id)
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    except Exception as e:
        logger.error(
            "job.detail.fetch.error", profile_id=profile_id, job_id=job_id, error=str(e), exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{profile_id}/{artifact_type}/{file_name}")
async def get_artifact(profile_id: str, artifact_type: str, file_name: str):
    """
    Serve artifact files (screenshots, videos, HAR files, etc).

    Args:
        profile_id: The profile ID
        artifact_type: Type of artifact (screenshots, videos, har, dom_snapshots)
        file_name: The artifact file name

    Returns:
        Static file content
    """
    try:
        # Validate artifact type
        valid_types = ["screenshots", "videos", "har", "dom_snapshots"]
        if artifact_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid artifact type: {artifact_type}")

        # Build safe path
        artifact_dir = Path(web_settings.artifacts_dir) / profile_id / artifact_type
        artifact_path = artifact_dir / file_name

        # Security check: ensure path is within artifacts directory
        if not artifact_path.resolve().is_relative_to(artifact_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid artifact path")

        if not artifact_path.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")

        logger.info(
            "artifact.serve",
            profile_id=profile_id,
            artifact_type=artifact_type,
            file_name=file_name,
        )

        # Return file based on type
        from fastapi.responses import FileResponse

        if artifact_type == "screenshots":
            return FileResponse(artifact_path, media_type="image/png")
        elif artifact_type == "videos":
            return FileResponse(artifact_path, media_type="video/webm")
        elif artifact_type == "har":
            return FileResponse(artifact_path, media_type="application/json")
        elif artifact_type == "dom_snapshots":
            return FileResponse(artifact_path, media_type="text/html")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "artifact.serve.error",
            profile_id=profile_id,
            artifact_type=artifact_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
