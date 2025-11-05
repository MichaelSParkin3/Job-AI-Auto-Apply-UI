"""CLI Orchestrator for Lever Auto‑Apply Assistant."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from . import job_discovery, profile_manager

# Auto-load .env if present (no-op if package missing)
try:  # pragma: no cover - optional
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv()
except Exception:
    pass
from .application_queue import ApplicationQueue, ApplicationStatus, Artifacts, Reason
from .config import load_settings
from .llm import load_llm_config
from .profile_manager import Profile, ProfileNotFoundError
from .telemetry import bind_timeline, log_event

if TYPE_CHECKING:
    from .browser_agent import LeverFormPlan

_BROWSER_RUNTIME: tuple[type[Any], type[Any], type[Any]] | None = None
_ENSURE_ALLOWED_DOMAIN: Callable[[str, Iterable[str]], None] | None = None


def _load_browser_runtime() -> tuple[type[Any], type[Any], type[Any]]:
    """Lazily import browser automation dependencies for apply flows."""
    global _BROWSER_RUNTIME
    if _BROWSER_RUNTIME is None:
        from browser_use.browser.session import BrowserSession

        from .browser_agent import LeverApplyAgent, LeverBrowserOptions

        _BROWSER_RUNTIME = (LeverBrowserOptions, LeverApplyAgent, BrowserSession)
    return _BROWSER_RUNTIME


def _ensure_allowed_domain_safe(url: str, allowed_domains: Iterable[str]) -> None:
    """Invoke ensure_allowed_domain without importing browser modules at import time."""
    global _ENSURE_ALLOWED_DOMAIN
    if _ENSURE_ALLOWED_DOMAIN is None:
        from .browser_agent import ensure_allowed_domain as _ensure_allowed

        _ENSURE_ALLOWED_DOMAIN = _ensure_allowed
    _ENSURE_ALLOWED_DOMAIN(url, list(allowed_domains))


# Internal: mirror discovery's browser channel resolver for apply


def _resolve_browser_channel(preferred: str | None) -> str | None:
    if not preferred:
        return "chrome"
    normalized = preferred.strip().lower()
    mapping = {
        "chrome": "chrome",
        "google chrome": "chrome",
        "chromium": "chromium",
        "msedge": "msedge",
        "edge": "msedge",
        "microsoft edge": "msedge",
    }
    return mapping.get(normalized, "chrome")


def _print_json(obj: object) -> None:
    """Serialize ``obj`` to JSON and emit it on stdout."""

    print(json.dumps(obj, ensure_ascii=False))


def cmd_discover(args: argparse.Namespace) -> int:
    """Execute the ``discover`` command and emit queue updates.

    Args:
        args: Parsed CLI arguments for the ``discover`` subcommand.

    Returns:
        int: Exit code (0 on success, 2 when no new items were found).

    """
    try:
        profile_obj = profile_manager.load_profile(args.profile)
    except ProfileNotFoundError:
        profile_obj = {"id": args.profile, "name": args.profile.title()}
    window_hours = _parse_window_hours(args.window)
    profile_id = _profile_id(profile_obj)
    queue = ApplicationQueue(profile_id)
    log_event(
        "discover.start",
        profile=profile_id,
        window_hours=window_hours,
        cap=args.cap,
    )

    discover_fn = job_discovery.discover_jobs
    if getattr(discover_fn, "__module__", "") == "job_ai_auto_apply_ui.job_discovery":
        discover_profile = _ensure_profile(profile_obj)
    else:
        discover_profile = profile_obj

    items = discover_fn(
        profile=discover_profile,
        window_hours=window_hours,
        cap=args.cap,
    )
    # Enqueue only real ApplicationItems; still pass through any contract-like items for JSON.
    to_enqueue = [item for item in items if hasattr(item, "hash")]
    if to_enqueue:
        queue.enqueue(to_enqueue)
    payload = {"items": [item.to_contract_dict() for item in items]}

    if args.json:
        _print_json(payload)
    else:
        profile_name = _profile_name(profile_obj)
        accepted = to_enqueue
        if accepted:
            print(f"Discovered {len(accepted)} new postings for profile '{profile_name}'.")
        else:
            print("No new postings discovered in the selected window.")
    log_event("discover.complete", profile=profile_id, new=len(items))
    return 0 if items else 2


def cmd_apply(args: argparse.Namespace) -> int:
    """Execute the ``apply`` command for the provided profile.

    Args:
        args: Parsed CLI arguments for the ``apply`` subcommand.

    Returns:
        int: Exit code ``0`` when all items were submitted, ``3`` when any failed,
            ``4`` when job ID not found.

    """
    try:
        profile_obj = profile_manager.load_profile(args.profile)
    except ProfileNotFoundError:
        profile_obj = {"id": args.profile, "name": args.profile.title()}
    # Apply CLI overrides via environment so downstream helpers pick them up
    import os as _os

    if hasattr(args, "use_llm_locator") and args.use_llm_locator is not None:
        _os.environ["AUTO_APPLY_USE_LLM_LOCATOR"] = "1" if args.use_llm_locator else "0"
    if getattr(args, "debug_resume_widget", False):
        _os.environ["AUTO_APPLY_DEBUG_RESUME_WIDGET"] = "1"
    if getattr(args, "resume_wait_timeout_seconds", None) is not None:
        _os.environ["AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS"] = str(
            args.resume_wait_timeout_seconds
        )

    mode = "auto" if args.auto else "supervised"
    llm_config = load_llm_config()
    if getattr(args, "llm_provider", None):
        llm_config.provider = args.llm_provider
    if getattr(args, "llm_model", None):
        llm_config.model = args.llm_model

    profile_id = _profile_id(profile_obj)
    profile_name = _profile_name(profile_obj)

    # Configure file logging if requested
    if getattr(args, "save_logs", False):
        from .telemetry import configure_file_logging

        log_dir = getattr(args, "logs_dir", "logs")
        log_file = configure_file_logging(log_dir, profile_id)
        if log_file:
            print(f"Logs will be saved to: {log_file}")
        else:
            print("Warning: Could not configure file logging")

    log_event("apply.start", profile=profile_id, mode=mode)
    log_event(
        "apply.llm_config",
        provider=llm_config.provider,
        model=llm_config.model,
    )

    # Extract review-mode and audit flags
    review_mode = getattr(args, "review_mode", False)
    audit_after_submit = not getattr(args, "no_audit_after_submit", False)
    job_id = getattr(args, "id", None)

    try:
        events = iter_apply_events(
            _ensure_profile(profile_obj),
            mode,
            review_mode=review_mode,
            audit_after_submit=audit_after_submit,
            job_id=job_id,
        )
    except LookupError as exc:
        # Job ID not found in queue
        if args.json:
            _print_json({"error": str(exc)})
        else:
            print(f"Error: {exc}")
        log_event("apply.job_not_found", profile=profile_id, job_id=job_id)
        return 4

    submitted = 0
    failed = 0
    saved_for_review = 0
    skipped = 0
    if args.json:
        for event in events:
            _print_json(event)
            if event["event"] == "submitted":
                submitted += 1
            if event["event"] == "failed":
                failed += 1
            if event["event"] == "captcha_blocked":
                failed += 1
            if event["event"] == "saved_for_review":
                saved_for_review += 1
            if event["event"] == "skipped":
                skipped += 1
            if event["event"] == "end":
                summary = event.get("summary", {})
                submitted = summary.get("submitted", submitted)
                failed = summary.get("failed", failed)
    else:
        print(f"Started apply session for '{profile_name}' in {mode} mode.")
        for event in events:
            if event["event"] == "item":
                print(f"Processing job {event['id']}...")
            elif event["event"] == "submitted":
                submitted += 1
                confirmation = event.get("confirmation_text", "n/a")
                print(f"Submitted {event['id']} (confirmation: {confirmation}).")
            elif event["event"] == "saved_for_review":
                saved_for_review += 1
                print(f"Saved for review {event['id']}: Form filled, review and submit manually.")
            elif event["event"] == "skipped":
                skipped += 1
                reason = event.get("reason", {})
                msg = reason.get("message", "User chose to skip")
                print(f"Skipped {event['id']}: {msg}")
            elif event["event"] == "captcha_blocked":
                failed += 1
                reason = event.get("reason", {})
                msg = reason.get("message", "hCaptcha detected")
                print(f"Captcha blocked {event['id']}: {msg}")
            elif event["event"] == "failed":
                failed += 1
                reason = event.get("reason", {})
                print(f"Failed {event['id']}: {reason.get('message', 'Unknown reason')}")
        # Build summary message
        summary_parts = [f"{submitted} submitted"]
        if skipped > 0:
            summary_parts.append(f"{skipped} skipped")
        if saved_for_review > 0:
            summary_parts.append(f"{saved_for_review} saved for review")
        summary_parts.append(f"{failed} failed")
        print(f"Session complete: {', '.join(summary_parts)}.")

    exit_code = 0 if failed == 0 else 3
    log_event("apply.complete", profile=profile_id, submitted=submitted, failed=failed)
    return exit_code


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a paused job from the persisted queues.

    Args:
        args: Parsed CLI arguments for the ``resume-job`` subcommand.

    Returns:
        int: Exit code ``0`` on success, ``4`` if not found, ``6`` on invalid_state.

    """
    submit_after_prefill = getattr(args, "submit", False)

    try:
        payload = resume_job(args.id, submit_after_prefill=submit_after_prefill)
    except LookupError:
        payload = {"id": args.id, "status": "not_found", "resumed_from_step": 0}
        if args.json:
            _print_json(payload)
        else:
            print(f"Job {args.id} not found in queues.")
        log_event("resume.missing", item=args.id)
        return 4
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        # Invalid state - pre.json missing or corrupt
        payload = {
            "id": args.id,
            "status": "invalid_state",
            "error": "pre.json missing or invalid",
        }
        if args.json:
            _print_json(payload)
        else:
            print(f"Cannot resume job {args.id}: {exc}")
        log_event("resume.invalid_state", item=args.id, error=str(exc))
        return 6

    if args.json:
        _print_json(payload)
    else:
        status = payload.get("status", "unknown")
        if status == "paused":
            print(f"Resumed job {payload['id']}, form prefilled. Review and submit manually.")
        elif status == "submitted":
            conf = payload.get("confirmation_text", "n/a")
            print(f"Resumed and submitted job {payload['id']} (confirmation: {conf}).")
        else:
            print(f"Resumed job {payload['id']} (status: {status}).")
    log_event("resume.success", item=payload["id"], status=payload.get("status"))
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Replay a job by resetting its status to IN_PROGRESS without opening browser.

    Args:
        args: Parsed CLI arguments for the ``replay-job`` subcommand.

    Returns:
        int: Exit code ``0`` on success or ``4`` if the item could not be located.

    """
    try:
        payload = replay_job(args.id)
    except LookupError:
        payload = {"id": args.id, "status": "not_found"}
        if args.json:
            _print_json(payload)
        else:
            print(f"Job {args.id} not found in queues.")
        log_event("replay.missing", item=args.id)
        return 4

    if args.json:
        _print_json(payload)
    else:
        print(f"Reset job {payload['id']} to retry from scratch.")
    log_event("replay.success", item=payload["id"], status=payload["status"])
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Execute the cleanup-artifacts command to delete old artifact files.

    Args:
        args: Parsed CLI arguments for the ``cleanup-artifacts`` subcommand.

    Returns:
        int: Exit code ``0`` on success, ``2`` when nothing matched, ``5`` on invalid args.

    """
    # older-than is required by argparse, but we validate it's positive
    older_than_days = args.older_than
    if older_than_days < 0:
        payload = {"error": "--older-than must be >= 0"}
        if args.json:
            _print_json(payload)
        else:
            print("Error: --older-than must be >= 0")
        return 5

    profile_filter = args.profile
    dry_run = args.dry_run

    result = cleanup_artifacts(
        older_than_days=older_than_days,
        profile_filter=profile_filter,
        dry_run=dry_run,
    )

    matched = result["matched"]
    deleted = result["deleted"]

    if args.json:
        _print_json(result)
    else:
        if dry_run:
            if matched > 0:
                print(f"Dry-run: would delete {matched} artifact files.")
                for file_path in result.get("files", []):
                    print(f"  - {file_path}")
            else:
                print("Dry-run: no artifacts matched the criteria.")
        else:
            if deleted > 0:
                print(f"Deleted {deleted} artifact files.")
            else:
                print("No artifacts matched the criteria.")

    log_event(
        "cleanup.complete",
        matched=matched,
        deleted=deleted,
        dry_run=dry_run,
        profile=profile_filter,
    )

    return 0 if matched > 0 else 2


def iter_apply_events(
    profile: Profile,
    mode: str,
    *,
    fetch_form: Callable[[str], str] | None = None,
    review_mode: bool = False,
    audit_after_submit: bool = True,
    job_id: str | None = None,
    prompt_callback: Callable[[str, list[str], dict | None], str] | None = None,
) -> Iterator[dict[str, object]]:
    """Yield apply events for streaming to the CLI.

    Args:
        profile: Active profile driving the application session.
        mode: ``"auto"`` or ``"supervised"`` mode indicator.
        fetch_form: Optional callable to retrieve HTML for a posting form.
        review_mode: If True, save pre-submit artifacts and skip submission.
        audit_after_submit: If True, capture post-submission screenshot (default).
        job_id: If provided, process only this specific job (auto-resets if needed).
        prompt_callback: Optional SYNC callback for interactive prompts in supervised mode.
            Called from nested asyncio.run() context, uses run_coroutine_threadsafe internally.
            Signature: (message, options, context) -> chosen_action (blocks until response)

    Yields:
        dict[str, object]: Event payloads following the apply contract schema.

    Raises:
        LookupError: If job_id provided but not found in queue.

    """
    profile = _ensure_profile(profile)
    queue = ApplicationQueue(profile.id)
    LeverBrowserOptions, LeverApplyAgent, BrowserSession = _load_browser_runtime()
    browser_options = LeverBrowserOptions.from_settings(profile=profile)
    agent = LeverApplyAgent(options=browser_options)
    submitted = 0
    failed = 0
    yield {"event": "start", "profile": profile.id}

    # Filter to specific job if requested
    if job_id:
        item = queue.get(job_id)
        if not item:
            raise LookupError(f"Job {job_id} not found in queue for profile {profile.id}")

        # Auto-reset status if needed (like replay-job does)
        if item.status in [
            ApplicationStatus.FAILED,
            ApplicationStatus.CAPTCHA_BLOCKED,
            ApplicationStatus.SUBMITTED,
        ]:
            previous_status = item.status.value
            item.status = ApplicationStatus.IN_PROGRESS
            item.last_updated_at = datetime.now(UTC)
            queue.update(item)
            log_event("apply.auto_reset", job_id=job_id, previous_status=previous_status)

        pending = [item]
    else:
        pending = queue.pending()

    log_event("apply.pending", profile=profile.id, count=len(pending))

    for item in pending:
        if item.status != ApplicationStatus.IN_PROGRESS:
            queue.resume(item.id)
        timeline = bind_timeline("apply", item=item.id)
        timeline.info("item.start")
        yield {"event": "item", "id": item.id, "status": ApplicationStatus.IN_PROGRESS.value}

        def _browser_apply_one() -> tuple[Artifacts | None, dict | None]:
            async def _run() -> tuple[Artifacts | None, dict | None]:
                # Create a fresh browser session per item for simplicity
                channel = _resolve_browser_channel(profile.preferred_browser)
                user_data_dir = str(profile.user_data_dir) if profile.user_data_dir else None
                # Apply stealth env (TZ/LANG/LC_ALL) then launch with supported kwargs only
                browser_options.apply_stealth_environment()
                session = BrowserSession(
                    headless=False,
                    channel=channel,
                    user_data_dir=user_data_dir,
                    keep_alive=True,
                    **browser_options.to_browser_use_kwargs(),
                )
                await session.start()
                try:
                    result = await agent.execute_in_browser(
                        session=session,
                        profile=profile,
                        item=item,
                        mode=mode,
                        review_mode=review_mode,
                        prompt_callback=prompt_callback,
                    )
                    if isinstance(result, Artifacts):
                        return result, None
                    else:
                        # Reason -> dict for event
                        reason = {"code": result.code, "message": result.message}
                        return None, reason
                finally:
                    try:
                        await session.stop()
                    except Exception:
                        pass

            return asyncio.run(_run())

        try:
            artifacts, reason = _browser_apply_one()
        except ValueError as exc:
            timeline.warning("form.fetch_failed", error=str(exc))
            log_event(
                "apply.form_fetch_failed",
                profile=profile.id,
                url=item.details.apply_url if item.details else item.url,
            )
            reason = {"code": "invalid_domain", "message": str(exc)}
            artifacts = None
        except Exception as exc:
            timeline.warning("form.runtime_error", error=str(exc))
            reason = {"code": "runtime_error", "message": str(exc)}
            artifacts = None

        if artifacts:
            queue.mark_submitted(item.id, artifacts)
            submitted += 1
            timeline.info(
                "item.submitted",
                confirmation_text=artifacts.confirmation_text,
                confirmation_id=artifacts.confirmation_id,
            )
            event_payload = {
                "event": "submitted",
                "id": item.id,
                "confirmation_text": artifacts.confirmation_text,
            }
            if artifacts.confirmation_id:
                event_payload["confirmation_id"] = artifacts.confirmation_id
            if artifacts.screenshot_after_path:
                event_payload["screenshot_after_path"] = artifacts.screenshot_after_path
            yield event_payload
        else:
            reason_code = reason.get("code", "failed")
            reason_obj = Reason(
                code=reason_code,
                message=reason.get("message", "Failed"),
            )

            # Handle user_skipped - mark as skipped without counting as failed
            if reason_code == "user_skipped":
                queue.mark_skipped(item.id, reason_obj)
                timeline.info("item.skipped", reason=reason)
                yield {"event": "skipped", "id": item.id, "reason": reason}

            # Handle saved_for_review - build artifacts from known paths
            elif reason_code == "saved_for_review":
                failed += 1
                settings = load_settings()
                artifact_dir = settings.artifacts_path(profile.id) / item.id
                pre_json_path = artifact_dir / "pre.json"
                pre_screenshot_path = artifact_dir / "pre-full.jpg"

                # Build artifacts object with saved state paths
                form_state = str(pre_json_path) if pre_json_path.exists() else None
                screenshot_before = (
                    str(pre_screenshot_path) if pre_screenshot_path.exists() else None
                )
                review_artifacts = Artifacts(
                    form_state_path=form_state,
                    screenshot_before_path=screenshot_before,
                )

                queue.mark_pending_review(item.id, review_artifacts)
                timeline.info(
                    "item.saved_for_review",
                    form_state_path=review_artifacts.form_state_path,
                )

                event_payload = {
                    "event": "saved_for_review",
                    "id": item.id,
                }
                if review_artifacts.form_state_path:
                    event_payload["form_state_path"] = review_artifacts.form_state_path
                if review_artifacts.screenshot_before_path:
                    event_payload["screenshot_before_path"] = (
                        review_artifacts.screenshot_before_path
                    )
                yield event_payload

            # Handle captcha_blocked specially - build artifacts from known paths
            elif reason_code == "captcha_blocked":
                failed += 1
                settings = load_settings()
                artifact_dir = settings.artifacts_path(profile.id) / item.id
                pre_json_path = artifact_dir / "pre.json"
                pre_screenshot_path = artifact_dir / "pre-full.jpg"

                # Build artifacts object if files exist
                captcha_artifacts = None
                if pre_json_path.exists() or pre_screenshot_path.exists():
                    form_state = str(pre_json_path) if pre_json_path.exists() else None
                    screenshot_before = (
                        str(pre_screenshot_path) if pre_screenshot_path.exists() else None
                    )
                    captcha_artifacts = Artifacts(
                        form_state_path=form_state,
                        screenshot_before_path=screenshot_before,
                    )

                queue.mark_captcha(item.id, reason_obj, captcha_artifacts)
                timeline.info("item.captcha_blocked", reason=reason)

                event_payload = {
                    "event": "captcha_blocked",
                    "id": item.id,
                    "reason": reason,
                }
                if captcha_artifacts:
                    if captcha_artifacts.form_state_path:
                        event_payload["form_state_path"] = captcha_artifacts.form_state_path
                    if captcha_artifacts.screenshot_before_path:
                        event_payload["screenshot_before_path"] = (
                            captcha_artifacts.screenshot_before_path
                        )
                yield event_payload
            else:
                queue.mark_failed(item.id, reason_obj)
                timeline.info("item.failed", reason=reason)
                yield {"event": "failed", "id": item.id, "reason": reason}

    yield {"event": "end", "summary": {"submitted": submitted, "failed": failed}}


def _profile_id(profile: Profile | Mapping[str, object]) -> str:
    if isinstance(profile, Profile):
        return profile.id
    if isinstance(profile, Mapping) and "id" in profile:
        return str(profile["id"])
    raise AttributeError("Profile missing id")


def _profile_name(profile: Profile | Mapping[str, object]) -> str:
    if isinstance(profile, Profile):
        return profile.name
    if isinstance(profile, Mapping):
        identifier = str(profile.get("id", "profile"))
        return str(profile.get("name", identifier.title()))
    return "profile"


def _ensure_profile(profile: Profile | Mapping[str, object]) -> Profile:
    if isinstance(profile, Profile):
        return profile
    if not isinstance(profile, Mapping):
        raise TypeError("Unsupported profile payload")

    profile_id = str(profile.get("id", "profile"))
    name = str(profile.get("name", profile_id.title()))
    resume_raw = profile.get("resume_path", "resume.pdf")
    defaults = _coerce_str_mapping(profile.get("defaults", {}))
    keywords = _coerce_keywords(profile.get("keywords", {}))
    prompts = _coerce_str_mapping(profile.get("prompts", {}))
    user_data_dir = profile.get("user_data_dir")
    preferred_browser = profile.get("preferred_browser")

    resolved_user_dir = Path(str(user_data_dir)).expanduser() if user_data_dir else None
    resolved_browser = str(preferred_browser) if preferred_browser else None

    return Profile(
        id=profile_id,
        name=name,
        resume_path=Path(str(resume_raw)),
        defaults=defaults,
        keywords=keywords,
        prompts=prompts,
        user_data_dir=resolved_user_dir,
        preferred_browser=resolved_browser,
    )


def _coerce_str_mapping(raw: object) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): str(value) for key, value in raw.items() if value is not None}


def _coerce_keywords(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, Mapping):
        return {}
    result: dict[str, list[str]] = {}
    for key, values in raw.items():
        if isinstance(values, Mapping):
            flattened: list[str] = []
            for inner in values.values():
                flattened.extend(_ensure_iterable(inner))
            result[str(key)] = flattened
        else:
            result[str(key)] = _ensure_iterable(values)
    return result


def _ensure_iterable(raw: object) -> list[str]:
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, Iterable):
        return [str(item) for item in raw if item is not None]
    if raw is None:
        return []
    return [str(raw)]


def _plan_to_payload(plan: "LeverFormPlan") -> dict[str, object]:
    """Convert a :class:`LeverFormPlan` into a serializable dictionary.

    Args:
        plan: Plan generated from form analysis.

    Returns:
        dict[str, object]: JSON-serializable payload of selectors and metadata.

    """

    return {
        "resume_input": plan.resume_input,
        "contact_fields": plan.contact_fields,
        "link_fields": plan.link_fields,
        "dynamic_questions": [
            {
                "prompt": question.prompt,
                "required": question.required,
                "answer_selector": question.answer_selector,
                "cache_key": question.cache_key,
            }
            for question in plan.dynamic_questions
        ],
        "submit_button": plan.submit_button,
        "captcha_selector": plan.captcha_selector,
    }


def _default_form_fetch(url: str) -> str:
    """Fetch Lever form HTML while enforcing allowed domain safety.

    Args:
        url: Target application form URL.

    Returns:
        str: Raw HTML contents of the requested form.

    Raises:
        ValueError: If the URL is outside the configured allow-list.

    """

    settings = load_settings()
    _ensure_allowed_domain_safe(url, settings.allowed_domains)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


def resume_job(job_id: str, submit_after_prefill: bool = False) -> dict[str, object]:
    """Resume a job by id with browser prefill and optional auto-submit.

    Args:
        job_id: Identifier returned from discovery/application queues.
        submit_after_prefill: If True, auto-submit after prefilling;
            if False, pause for review.

    Returns:
        dict[str, object]: Payload with id, status (paused|submitted),
            and optional confirmation fields.

    Raises:
        LookupError: If the job cannot be found in any persisted queue file.
        FileNotFoundError: If pre.json is missing for the job.
        json.JSONDecodeError: If pre.json is corrupt.

    """
    from . import saved_state

    queue_dir = Path.cwd() / "data" / "queues"
    queue_dir.mkdir(parents=True, exist_ok=True)

    # Find the job in queues
    profile_id = None
    queue = None
    item = None

    for queue_path in queue_dir.glob("*.json"):
        profile_id = queue_path.stem
        queue = ApplicationQueue(profile_id)
        item = queue.get(job_id)
        if item:
            break

    if not item or not profile_id or not queue:
        raise LookupError(job_id)

    # Load pre.json from artifacts
    settings = load_settings()
    artifact_dir = settings.artifacts_path(profile_id) / job_id
    pre_json_path = artifact_dir / "pre.json"

    if not pre_json_path.exists():
        raise FileNotFoundError(f"pre.json not found at {pre_json_path}")

    # Read saved state - may raise JSONDecodeError
    saved_form_state = saved_state.read_pre_state(pre_json_path)

    # Load profile for browser session
    profile = profile_manager.load_profile(profile_id)

    # Transition to IN_PROGRESS
    try:
        queue.resume(job_id)
    except ValueError:
        item.status = ApplicationStatus.IN_PROGRESS
        item.last_updated_at = datetime.now(UTC)
        queue.update(item)

    # Full browser prefill + submit implementation
    async def _resume_browser() -> dict[str, object]:
        from browser_use.browser.session import BrowserSession

        from .browser_agent import prefill_from_saved_state

        # Create browser session
        LeverBrowserOptions, _, _ = _load_browser_runtime()
        browser_options = LeverBrowserOptions.from_settings(profile=profile)
        browser_options.apply_stealth_environment()

        channel = _resolve_browser_channel(profile.preferred_browser)
        user_data_dir = str(profile.user_data_dir) if profile.user_data_dir else None

        session = BrowserSession(
            headless=False,
            channel=channel,
            user_data_dir=user_data_dir,
            keep_alive=True,
            **browser_options.to_browser_use_kwargs(),
        )
        await session.start()

        try:
            # Navigate to saved URL
            page = await session.get_current_page() or await session.new_page()
            apply_url = saved_form_state.get("apply_url") or saved_form_state.get("url")
            await page.goto(apply_url)
            log_event("resume.navigate", url=apply_url, job_id=job_id)

            # Prefill form from saved state
            await prefill_from_saved_state(page, saved_form_state)

            # Give browser time to render the filled values in DOM
            await asyncio.sleep(1.5)

            if submit_after_prefill:
                # Submit and capture confirmation
                submit_selector = saved_form_state.get("plan", {}).get(
                    "submit_button", "button#btn-submit"
                )
                await page.locator(submit_selector).click()
                await asyncio.sleep(2.0)
                log_event("resume.submitted", job_id=job_id)

                # Extract confirmation text
                confirmation_text = await page.text_content("body")
                confirmation_text = confirmation_text[:500] if confirmation_text else "submitted"

                return {
                    "id": job_id,
                    "status": "submitted",
                    "confirmation_text": confirmation_text,
                    "confirmation_id": None,
                }
            else:
                # Pause for manual review
                log_event("resume.paused", job_id=job_id)
                print(
                    f"\nJob {job_id} prefilled and ready. "
                    "Review the form, then press Enter to continue..."
                )
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass

                return {
                    "id": job_id,
                    "status": "paused",
                    "message": "Form prefilled from saved state.",
                }
        finally:
            try:
                await session.stop()
            except Exception:
                pass

    return asyncio.run(_resume_browser())


def replay_job(job_id: str) -> dict[str, object]:
    """Reset a job to IN_PROGRESS status without opening browser.

    Args:
        job_id: Identifier returned from discovery/application queues.

    Returns:
        dict[str, object]: Payload with id and status set to in_progress.

    Raises:
        LookupError: If the job cannot be found in any persisted queue file.

    """
    queue_dir = Path.cwd() / "data" / "queues"
    queue_dir.mkdir(parents=True, exist_ok=True)

    for queue_path in queue_dir.glob("*.json"):
        profile_id = queue_path.stem
        queue = ApplicationQueue(profile_id)
        item = queue.get(job_id)
        if item:
            # Reset to IN_PROGRESS without browser
            try:
                queue.resume(job_id)
            except ValueError:
                item.status = ApplicationStatus.IN_PROGRESS
                item.last_updated_at = datetime.now(UTC)
                queue.update(item)

            return {
                "id": job_id,
                "status": ApplicationStatus.IN_PROGRESS.value,
            }

    raise LookupError(job_id)


def cleanup_artifacts(
    older_than_days: int,
    profile_filter: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    """Delete artifact files older than the specified age.

    Args:
        older_than_days: Minimum age in days for files to be deleted.
        profile_filter: If provided, only delete artifacts for this profile.
        dry_run: If True, list matched files without deleting.

    Returns:
        dict[str, object]: Result payload with matched count, deleted count, and optional file list.

    """
    from datetime import timedelta

    settings = load_settings()
    artifacts_root = Path(settings.artifacts_root)

    if not artifacts_root.exists():
        return {"matched": 0, "deleted": 0, "files": []}

    cutoff_time = datetime.now(UTC) - timedelta(days=older_than_days)
    matched_files: list[str] = []

    # Scan artifacts directory
    if profile_filter:
        # Only scan specific profile
        profile_dirs = [artifacts_root / profile_filter]
    else:
        # Scan all profiles
        profile_dirs = [p for p in artifacts_root.iterdir() if p.is_dir()]

    for profile_dir in profile_dirs:
        if not profile_dir.exists():
            continue

        # Iterate through item directories
        for item_dir in profile_dir.iterdir():
            if not item_dir.is_dir():
                continue

            # Check all files in the item directory
            for artifact_file in item_dir.iterdir():
                if not artifact_file.is_file():
                    continue

                # Get file modification time
                mtime = datetime.fromtimestamp(artifact_file.stat().st_mtime, tz=UTC)

                if mtime < cutoff_time:
                    matched_files.append(str(artifact_file))

    deleted_count = 0

    if dry_run:
        log_event(
            "cleanup.preview",
            matched=len(matched_files),
            profile=profile_filter,
            older_than_days=older_than_days,
        )
    else:
        log_event(
            "cleanup.apply",
            matched=len(matched_files),
            profile=profile_filter,
            older_than_days=older_than_days,
        )
        # Actually delete the files
        for file_path in matched_files:
            try:
                Path(file_path).unlink()
                deleted_count += 1
            except Exception:
                # Ignore deletion errors and continue
                pass

    result: dict[str, object] = {
        "matched": len(matched_files),
        "deleted": deleted_count if not dry_run else 0,
    }

    if dry_run:
        result["files"] = matched_files

    return result


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI argument parser.

    Returns:
        argparse.ArgumentParser: Parser configured with all subcommands.

    """
    parser = argparse.ArgumentParser(
        prog="auto-apply",
        description="Lever Auto‑Apply Assistant. Use --json for machine-readable outputs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_discover = sub.add_parser("discover", help="Discover Lever postings")
    p_discover.add_argument("--profile", required=True)
    p_discover.add_argument("--window", default="24h")
    p_discover.add_argument("--cap", type=int, default=10)
    p_discover.add_argument("--json", action="store_true")
    p_discover.set_defaults(func=cmd_discover)

    p_apply = sub.add_parser("apply", help="Apply to queued postings")
    mode = p_apply.add_mutually_exclusive_group()
    mode.add_argument("--auto", action="store_true")
    mode.add_argument("--supervised", action="store_true")
    p_apply.add_argument("--profile", required=True)
    p_apply.add_argument("--id", help="Process only this specific job ID (auto-resets if needed)")
    p_apply.add_argument("--json", action="store_true")
    p_apply.add_argument("--llm-provider", help="Override configured LLM provider")
    p_apply.add_argument("--llm-model", help="Override configured LLM model")
    # Resume upload tuning / diagnostics
    p_apply.add_argument(
        "--use-llm-locator",
        action="store_true",
        help=(
            "Enable LLM-powered element finding for resume upload "
            "(sets AUTO_APPLY_USE_LLM_LOCATOR=1)"
        ),
    )
    p_apply.add_argument(
        "--no-use-llm-locator",
        dest="use_llm_locator",
        action="store_false",
        help=(
            "Disable LLM-powered element finding for resume upload "
            "(sets AUTO_APPLY_USE_LLM_LOCATOR=0)"
        ),
    )
    p_apply.add_argument(
        "--debug-resume-widget",
        action="store_true",
        help=(
            "Emit structured widget snapshot when upload not detected "
            "(AUTO_APPLY_DEBUG_RESUME_WIDGET=1)"
        ),
    )
    p_apply.add_argument(
        "--resume-wait-timeout-seconds",
        type=int,
        help=("Override wait for upload success signals (AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS)"),
    )
    p_apply.add_argument(
        "--save-logs",
        action="store_true",
        help="Save structured logs to timestamped file in logs/ directory",
    )
    p_apply.add_argument(
        "--logs-dir",
        default="logs",
        help="Directory for log files (default: logs/)",
    )
    p_apply.add_argument(
        "--review-mode",
        action="store_true",
        help="Save pre-submit artifacts and pause without submitting",
    )
    audit_group = p_apply.add_mutually_exclusive_group()
    audit_group.add_argument(
        "--audit-after-submit",
        action="store_true",
        help="Capture post-submission screenshot (default behavior)",
    )
    audit_group.add_argument(
        "--no-audit-after-submit",
        action="store_true",
        help="Skip post-submission screenshot capture",
    )
    p_apply.set_defaults(func=cmd_apply)

    p_resume = sub.add_parser("resume-job", help="Resume a blocked job")
    p_resume.add_argument("id", help="Application item id")
    p_resume.add_argument("--json", action="store_true")
    p_resume.add_argument(
        "--submit",
        action="store_true",
        help="Auto-submit after prefilling form (default: pause for review)",
    )
    p_resume.set_defaults(func=cmd_resume)

    p_replay = sub.add_parser("replay-job", help="Reset job to retry from scratch")
    p_replay.add_argument("id", help="Application item id")
    p_replay.add_argument("--json", action="store_true")
    p_replay.set_defaults(func=cmd_replay)

    p_cleanup = sub.add_parser("cleanup-artifacts", help="Delete old artifact files")
    p_cleanup.add_argument(
        "--profile",
        help="Filter artifacts for specific profile (default: all profiles)",
    )
    p_cleanup.add_argument(
        "--older-than",
        type=int,
        required=True,
        metavar="DAYS",
        help="Delete artifacts older than this many days (REQUIRED)",
    )
    p_cleanup.add_argument(
        "--dry-run",
        action="store_true",
        help="List matched files without deleting",
    )
    p_cleanup.add_argument("--json", action="store_true")
    p_cleanup.set_defaults(func=cmd_cleanup)

    return parser


def _parse_window_hours(value: str) -> int:
    """Parse shorthand duration strings into integer hour counts.

    Args:
        value: Duration string such as ``"24h"`` or ``"7d"``.

    Returns:
        int: Number of hours represented by the input (minimum of 1).

    """
    value = value.strip().lower()
    if value.endswith("h"):
        return max(1, int(value[:-1]))
    if value.endswith("d"):
        return max(1, int(value[:-1]) * 24)
    if value.endswith("w"):
        return max(1, int(value[:-1]) * 24 * 7)
    return max(1, int(value))


def main(argv: Iterable[str] | None = None) -> int:
    """Entry point for the auto-apply CLI.

    Args:
        argv: Optional argument list to parse instead of ``sys.argv``.

    Returns:
        int: Exit code emitted by the chosen subcommand handler.

    """
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
