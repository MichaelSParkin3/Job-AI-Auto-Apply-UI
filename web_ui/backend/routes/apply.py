"""Routes for apply command."""

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException

from job_ai_auto_apply_ui.profile_manager import load_profile

from ..models.command import ApplyRequest, ApplyResponse

router = APIRouter()
logger = structlog.get_logger()

# In-memory task storage (use Redis/DB for production)
# Maps task_id -> {request, status, created_at, started_at, completed_at}
active_tasks = {}


@router.post("/apply", response_model=ApplyResponse)
async def apply(request: ApplyRequest):
    """
    Start apply command and return WebSocket URL for progress.

    Client should immediately connect to /ws/apply/{task_id} to receive events.

    Args:
        request: ApplyRequest with profile_id and optional flags

    Returns:
        ApplyResponse with task_id and websocket_url
    """
    try:
        # Validate profile exists
        profile = load_profile(request.profile_id)

        # Create unique task ID
        task_id = str(uuid.uuid4())

        # Store task configuration
        active_tasks[task_id] = {
            "request": request,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "apply.task.created",
            task_id=task_id,
            profile_id=request.profile_id,
            job_id=request.job_id,
        )

        return ApplyResponse(
            task_id=task_id,
            message=f"Apply task created for profile '{request.profile_id}'",
            websocket_url=f"/ws/apply/{task_id}",
        )

    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=request.profile_id)
        raise HTTPException(
            status_code=404, detail=f"Profile '{request.profile_id}' not found"
        )
    except Exception as e:
        logger.error("apply.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
