"""WebSocket routes for real-time streaming."""

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from job_ai_auto_apply_ui.orchestrator import iter_apply_events
from job_ai_auto_apply_ui.profile_manager import load_profile

from .apply import active_tasks

router = APIRouter()
logger = structlog.get_logger()


@router.websocket("/apply/{task_id}")
async def websocket_apply(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time apply progress streaming.

    Events streamed as JSON:
    - {"type": "apply.start", "profile_id": "...", "timestamp": "..."}
    - {"type": "item.start", "item_id": "...", "company": "...", "title": "..."}
    - {"type": "item.submitted", "item_id": "...", "confirmation_id": "..."}
    - {"type": "item.failed", "item_id": "...", "reason": {...}}
    - {"type": "apply.end", "submitted": 5, "failed": 1}
    - {"type": "error", "message": "..."}

    Args:
        websocket: WebSocket connection
        task_id: Task ID from /api/apply response
    """
    await websocket.accept()

    try:
        # Validate task exists
        if task_id not in active_tasks:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Task {task_id} not found",
                }
            )
            await websocket.close()
            return

        task = active_tasks[task_id]
        request = task["request"]

        # Load profile
        try:
            profile = load_profile(request.profile_id)
        except Exception as e:
            logger.error(
                "websocket.profile.load.failed",
                task_id=task_id,
                profile_id=request.profile_id,
                error=str(e),
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Failed to load profile: {str(e)}",
                }
            )
            await websocket.close()
            return

        # Update task status
        active_tasks[task_id]["status"] = "running"

        logger.info(
            "websocket.apply.start",
            task_id=task_id,
            profile_id=request.profile_id,
        )

        try:
            # Stream apply events
            async for event in iter_apply_events(
                profile=profile,
                mode="supervised" if request.supervised else "auto",
                job_id=request.job_id,
                llm_provider=request.llm_provider,
                llm_model=request.llm_model,
                use_llm_locator=request.use_llm_locator,
                debug_resume_widget=request.debug_resume_widget,
                resume_wait_timeout_seconds=request.resume_wait_timeout_seconds,
                review_mode=request.review_mode,
            ):
                # Forward event to WebSocket client
                await websocket.send_json(event)

            # Update task status
            active_tasks[task_id]["status"] = "completed"
            logger.info("websocket.apply.complete", task_id=task_id)

        except Exception as e:
            logger.error(
                "websocket.apply.error",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Apply failed: {str(e)}",
                }
            )
            active_tasks[task_id]["status"] = "failed"

    except WebSocketDisconnect:
        logger.info("websocket.disconnected", task_id=task_id)
        if task_id in active_tasks:
            active_tasks[task_id]["status"] = "disconnected"

    except Exception as e:
        logger.error("websocket.error", task_id=task_id, error=str(e), exc_info=True)
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": str(e),
                }
            )
        except Exception as send_error:
            logger.error(
                "websocket.send.error",
                task_id=task_id,
                error=str(send_error),
            )

    finally:
        try:
            await websocket.close()
        except Exception as close_error:
            logger.warning("websocket.close.error", error=str(close_error))
