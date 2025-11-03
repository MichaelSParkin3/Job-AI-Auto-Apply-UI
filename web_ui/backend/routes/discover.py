"""Routes for job discovery."""

import asyncio
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from job_ai_auto_apply_ui.application_queue import ApplicationQueue
from job_ai_auto_apply_ui.job_discovery import discover_jobs
from job_ai_auto_apply_ui.profile_manager import load_profile

from ..models.command import DiscoverRequest, DiscoverResponse

router = APIRouter()
logger = structlog.get_logger()

# Store discover task status (use Redis/DB for production)
discover_tasks = {}


def _parse_window_to_hours(window: str) -> int:
    """Parse window string (e.g., '24h', '7d', '1w') to hours."""
    if window.endswith("h"):
        return int(window[:-1])
    elif window.endswith("d"):
        return int(window[:-1]) * 24
    elif window.endswith("w"):
        return int(window[:-1]) * 24 * 7
    elif window.endswith("m"):
        return int(window[:-1]) * 24 * 30
    else:
        return 24  # default


async def run_discover_task(request: DiscoverRequest) -> dict:
    """Background task to run discover command."""
    task_id = f"{request.profile_id}_{datetime.utcnow().timestamp()}"

    try:
        logger.info(
            "discover.start",
            profile_id=request.profile_id,
            window=request.window,
            cap=request.cap,
        )

        # Load profile
        profile = load_profile(request.profile_id)

        # Convert window string to hours
        window_hours = _parse_window_to_hours(request.window)

        # Call discover_jobs in thread pool to avoid asyncio.run() conflict
        # discover_jobs is synchronous but uses asyncio.run() internally
        items = await asyncio.to_thread(
            discover_jobs, profile=profile, window_hours=window_hours, cap=request.cap
        )

        # Filter real ApplicationItems
        to_enqueue = [item for item in items if hasattr(item, "hash")]

        # Enqueue items
        if to_enqueue:
            queue = ApplicationQueue(request.profile_id)
            queue.enqueue(to_enqueue)

        logger.info(
            "discover.complete",
            profile_id=request.profile_id,
            count=len(to_enqueue),
            total_items=len(items),
        )

        # Store task result
        discover_tasks[task_id] = {
            "status": "completed",
            "items_discovered": len(to_enqueue),
            "completed_at": datetime.utcnow().isoformat(),
        }

        return {
            "success": True,
            "items_discovered": len(to_enqueue),
            "message": f"Discovered {len(to_enqueue)} new postings for profile '{request.profile_id}'",
        }

    except Exception as e:
        logger.error(
            "discover.failed",
            profile_id=request.profile_id,
            error=str(e),
            exc_info=True,
        )
        discover_tasks[task_id] = {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }
        raise


@router.post("/discover", response_model=DiscoverResponse)
async def discover(request: DiscoverRequest, background_tasks: BackgroundTasks):
    """
    Trigger discover command to find new job postings.

    This endpoint returns immediately and runs discovery in background.
    Poll the queue endpoint to see new items.

    Args:
        request: DiscoverRequest with profile_id, window, and cap
        background_tasks: FastAPI background tasks

    Returns:
        DiscoverResponse with status and WebSocket URL
    """
    try:
        # Validate profile exists
        profile = load_profile(request.profile_id)

        # Add background task
        background_tasks.add_task(run_discover_task, request)

        logger.info(
            "discover.task.created",
            profile_id=request.profile_id,
            window=request.window,
            cap=request.cap,
        )

        return DiscoverResponse(
            success=True,
            items_discovered=0,
            message=f"Discover started for profile '{request.profile_id}' (window: {request.window}, cap: {request.cap}). Items will appear in the queue shortly.",
            profile_id=request.profile_id,
        )

    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=request.profile_id)
        raise HTTPException(
            status_code=404, detail=f"Profile '{request.profile_id}' not found"
        )
    except Exception as e:
        logger.error("discover.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
