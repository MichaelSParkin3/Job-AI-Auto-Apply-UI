"""WebSocket routes for real-time streaming and bidirectional communication."""

import asyncio
import os
import uuid
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Optional, List

from job_ai_auto_apply_ui.orchestrator import iter_apply_events
from job_ai_auto_apply_ui.profile_manager import load_profile

from .apply import active_tasks
from ..models.events import ActionPromptOption, PromptContext

router = APIRouter()
logger = structlog.get_logger()

# Global pending prompts for bidirectional communication
# Maps prompt_id -> asyncio.Queue for response
pending_prompts: Dict[str, asyncio.Queue] = {}


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


async def emit_action_prompt(
    websocket: WebSocket,
    message: str,
    options: List[ActionPromptOption],
    context: Optional[PromptContext] = None,
    timeout_seconds: int = 300,
) -> str:
    """
    Emit action prompt to client and wait for response.

    Args:
        websocket: WebSocket connection to send prompt on
        message: Prompt message to display
        options: List of action options for user to choose
        context: Optional context (company, title, screenshot, etc.)
        timeout_seconds: Timeout waiting for response

    Returns:
        Action chosen by user, or "timeout" if no response received
    """
    prompt_id = str(uuid.uuid4())
    response_queue: asyncio.Queue = asyncio.Queue()
    pending_prompts[prompt_id] = response_queue

    try:
        # Send prompt to client
        logger.info(
            "websocket.prompt.emit",
            prompt_id=prompt_id,
            message=message,
            option_count=len(options),
        )
        await websocket.send_json(
            {
                "type": "prompt.action_required",
                "prompt_id": prompt_id,
                "message": message,
                "options": [opt.model_dump() for opt in options],
                "context": context.model_dump() if context else None,
                "timeout_seconds": timeout_seconds,
            }
        )

        # Wait for response (with timeout)
        response = await asyncio.wait_for(response_queue.get(), timeout=timeout_seconds)
        action = response.get("action", "timeout")
        logger.info(
            "websocket.prompt.response",
            prompt_id=prompt_id,
            action=action,
        )
        return action

    except asyncio.TimeoutError:
        logger.warning(
            "websocket.prompt.timeout",
            prompt_id=prompt_id,
            timeout_seconds=timeout_seconds,
        )
        return "timeout"
    finally:
        pending_prompts.pop(prompt_id, None)


def _transform_apply_event(event: dict) -> dict:
    """
    Transform backend event format to frontend event format.

    Backend sends: {"event": "start", "profile": "..."}
    Frontend expects: {"type": "apply.start", "profile_id": "..."}

    High-level events are transformed to structured types.
    All other events are transformed to verbose log events for debugging.
    """
    backend_event = event.get("event")

    # High-level events with explicit transformation
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
        # Transform all other events to verbose log events for terminal view
        # Extract data fields, excluding metadata
        data = {k: v for k, v in event.items() if k not in ["event", "timestamp", "level"]}
        return {
            "type": "log.verbose",
            "timestamp": event.get("timestamp", ""),
            "event": backend_event,
            "level": event.get("level", "info"),
            "data": data,
        }


async def _iter_apply_events_async(*args, **kwargs):
    """
    Async wrapper for iter_apply_events sync generator.

    Runs the sync generator in a thread pool to avoid asyncio.run() conflict.
    Also transforms event format from backend to frontend expectations.
    """
    # Sentinel value to signal end of iteration
    _DONE = object()

    # Create an iterator in a thread-safe way
    iterator = None

    def _get_iterator():
        nonlocal iterator
        if iterator is None:
            iterator = iter_apply_events(*args, **kwargs)
        return iterator

    def _next_or_done(it):
        """Get next item or return sentinel if done (catches StopIteration in thread)."""
        try:
            return next(it)
        except StopIteration:
            return _DONE

    while True:
        # Run next() in a thread pool, catching StopIteration inside the thread
        event = await asyncio.to_thread(_next_or_done, _get_iterator())

        if event is _DONE:
            break

        # Transform event to match frontend format
        transformed = _transform_apply_event(event)
        yield transformed


@router.websocket("/apply/{task_id}")
async def websocket_apply(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time apply progress streaming with bidirectional support.

    **Outbound Events** streamed as JSON:
    - {"type": "apply.start", "profile_id": "...", "timestamp": "..."}
    - {"type": "item.start", "item_id": "...", "company": "...", "title": "..."}
    - {"type": "item.submitted", "item_id": "...", "confirmation_id": "..."}
    - {"type": "item.failed", "item_id": "...", "reason": {...}}
    - {"type": "prompt.action_required", "prompt_id": "...", "message": "...", "options": [...]}
    - {"type": "apply.end", "submitted": 5, "failed": 1}
    - {"type": "error", "message": "..."}

    **Inbound Messages** from client:
    - {"type": "user_response", "prompt_id": "...", "action": "submit|skip|block"}

    Args:
        websocket: WebSocket connection
        task_id: Task ID from /api/apply response
    """
    logger.info("websocket.apply.connection_attempt", task_id=task_id)
    await websocket.accept()
    logger.info("websocket.apply.connection_accepted", task_id=task_id)

    receiver_task = None

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

        # Create prompt callback for supervised mode
        # Note: This is a SYNC callback that bridges to async WebSocket operations
        # It's called from within asyncio.run() in the CLI, so it must be synchronous
        # and use run_coroutine_threadsafe to communicate with the FastAPI event loop

        # Capture the FastAPI event loop for thread-safe communication
        fastapi_loop = asyncio.get_running_loop()

        def prompt_callback(
            message: str, options: List[str], context: Optional[dict] = None
        ) -> str:
            """
            Sync callback for CLI to request user input via WebSocket.

            Bridges between the nested asyncio.run() loop (in orchestrator) and
            the FastAPI event loop by using run_coroutine_threadsafe.

            Args:
                message: Prompt message
                options: List of action options ['submit', 'skip', 'block']
                context: Dict with optional keys: item_id, company, title, screenshot_path

            Returns:
                User's choice or 'timeout'
            """
            try:
                # Build action options
                action_options = [
                    ActionPromptOption(
                        action=opt,
                        label=opt.title(),  # Simple: "Submit" -> "Submit"
                        key=None,  # Could map Submit->Enter, Skip->S, Block->B
                    )
                    for opt in options
                ]

                # Build context object if provided
                prompt_context = None
                if context:
                    prompt_context = PromptContext(
                        item_id=context.get("item_id"),
                        company=context.get("company"),
                        title=context.get("title"),
                        screenshot_path=context.get("screenshot_path"),
                    )

                # Create async task in the FastAPI event loop
                async def _emit():
                    return await emit_action_prompt(
                        websocket, message, action_options, prompt_context
                    )

                # Submit to FastAPI event loop and block for result
                future = asyncio.run_coroutine_threadsafe(_emit(), fastapi_loop)
                result = future.result(timeout=300)  # 5 minute timeout
                logger.info("websocket.prompt_callback_success", action=result)
                return result

            except (BrokenPipeError, ConnectionError, OSError) as e:
                # Connection-level errors (broken pipe, socket closed, etc)
                logger.warning(
                    "websocket.prompt_callback_connection_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                # Auto-continue by returning submit to gracefully handle disconnection
                return "submit"
            except Exception as e:
                logger.error(
                    "websocket.prompt_callback_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                # Return timeout action to gracefully fail over
                return "timeout"

        # Store callback in task for later access
        task["prompt_callback"] = prompt_callback

        # Start background task to receive client messages (responses)
        async def receive_client_messages():
            """Background task to receive user responses from client."""
            try:
                while True:
                    data = await websocket.receive_json()
                    if data.get("type") == "user_response":
                        prompt_id = data.get("prompt_id")
                        if prompt_id in pending_prompts:
                            logger.info(
                                "websocket.message.received",
                                prompt_id=prompt_id,
                                action=data.get("action"),
                            )
                            await pending_prompts[prompt_id].put(data)
                        else:
                            logger.warning(
                                "websocket.message.unknown_prompt",
                                prompt_id=prompt_id,
                            )
                    else:
                        logger.warning(
                            "websocket.message.unknown_type",
                            message_type=data.get("type"),
                        )
            except Exception as e:
                logger.error("websocket.receive.error", error=str(e), exc_info=True)

        receiver_task = asyncio.create_task(receive_client_messages())

        try:
            # Apply request settings as environment variables (picked up by config loader)
            _apply_request_settings(request)

            # Stream apply events using async wrapper to handle sync generator with asyncio.run() inside
            async for event in _iter_apply_events_async(
                profile=profile,
                mode="supervised" if request.supervised else "auto",
                review_mode=request.review_mode,
                job_id=request.job_id,
                prompt_callback=prompt_callback,
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
        # Cancel background receiver task
        if receiver_task:
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

        try:
            await websocket.close()
        except Exception as close_error:
            logger.warning("websocket.close.error", error=str(close_error))
