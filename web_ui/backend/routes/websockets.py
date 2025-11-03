"""WebSocket routes for real-time streaming."""

import asyncio
import os
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from job_ai_auto_apply_ui.orchestrator import iter_apply_events
from job_ai_auto_apply_ui.profile_manager import load_profile

from .apply import active_tasks

router = APIRouter()
logger = structlog.get_logger()


def _apply_request_settings(request) -> None:
    """Apply ApplyRequest settings as environment variables for the apply session."""
    # Override LLM provider if specified
    if request.llm_provider:
        os.environ["LLM_PROVIDER"] = request.llm_provider

    # Override LLM model if specified
    if request.llm_model:
        os.environ["LLM_MODEL"] = request.llm_model

    # Override feature flags if specified
    if request.use_llm_locator:
        os.environ["AUTO_APPLY_USE_LLM_LOCATOR"] = "1"

    if request.debug_resume_widget:
        os.environ["AUTO_APPLY_DEBUG_RESUME_WIDGET"] = "1"

    # Override resume timeout if specified
    if request.resume_wait_timeout_seconds:
        os.environ["AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS"] = str(request.resume_wait_timeout_seconds)


def _transform_apply_event(event: dict) -> dict:
    """
    Transform backend event format to frontend event format.

    Backend sends: {"event": "start", "profile": "..."}
    Frontend expects: {"type": "apply.start", "profile_id": "..."}
    """
    backend_event = event.get("event")

    if backend_event == "start":
        return {
            "type": "apply.start",
            "profile_id": event.get("profile"),
            "timestamp": event.get("timestamp"),
        }
    elif backend_event == "item":
        return {
            "type": "item.start",
            "item_id": event.get("id"),
            "status": event.get("status"),
        }
    elif backend_event == "submitted":
        return {
            "type": "item.submitted",
            "item_id": event.get("id"),
            "confirmation_id": event.get("confirmation_id"),
            "confirmation_text": event.get("confirmation_text"),
            "screenshot_after_path": event.get("screenshot_after_path"),
        }
    elif backend_event == "saved_for_review":
        return {
            "type": "item.saved_for_review",
            "item_id": event.get("id"),
            "form_state_path": event.get("form_state_path"),
            "screenshot_before_path": event.get("screenshot_before_path"),
        }
    elif backend_event == "skipped":
        return {
            "type": "item.skipped",
            "item_id": event.get("id"),
            "reason": event.get("reason"),
        }
    elif backend_event == "captcha_blocked":
        return {
            "type": "item.captcha_blocked",
            "item_id": event.get("id"),
            "reason": event.get("reason"),
            "form_state_path": event.get("form_state_path"),
            "screenshot_before_path": event.get("screenshot_before_path"),
        }
    elif backend_event == "failed":
        return {
            "type": "item.failed",
            "item_id": event.get("id"),
            "reason": event.get("reason"),
        }
    elif backend_event == "end":
        summary = event.get("summary", {})
        return {
            "type": "apply.end",
            "submitted": summary.get("submitted", 0),
            "failed": summary.get("failed", 0),
        }
    else:
        # Passthrough for error events or unknown types
        return event


async def _iter_apply_events_async(*args, **kwargs):
    """
    Async wrapper for iter_apply_events sync generator.

    Runs the sync generator in a thread pool to avoid asyncio.run() conflict.
    Also transforms event format from backend to frontend expectations.
    """
    # Create an iterator in a thread-safe way
    iterator = None

    def _get_iterator():
        nonlocal iterator
        if iterator is None:
            iterator = iter_apply_events(*args, **kwargs)
        return iterator

    while True:
        try:
            # Run next() in a thread pool to avoid blocking the event loop
            # and to allow the sync generator's asyncio.run() to work
            event = await asyncio.to_thread(lambda it=_get_iterator(): next(it))
            # Transform event to match frontend format
            transformed = _transform_apply_event(event)
            yield transformed
        except StopIteration:
            break


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
            # Apply request settings as environment variables (picked up by config loader)
            _apply_request_settings(request)

            # Stream apply events using async wrapper to handle sync generator with asyncio.run() inside
            async for event in _iter_apply_events_async(
                profile=profile,
                mode="supervised" if request.supervised else "auto",
                review_mode=request.review_mode,
                job_id=request.job_id,
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
