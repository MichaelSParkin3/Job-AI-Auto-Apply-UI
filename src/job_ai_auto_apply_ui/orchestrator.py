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
            print(
                "Discovered "
                f"{len(accepted)} new postings for profile '{profile_name}'."
            )
        else:
            print("No new postings discovered in the selected window.")
    log_event("discover.complete", profile=profile_id, new=len(items))
    return 0 if items else 2


def cmd_apply(args: argparse.Namespace) -> int:
    """Execute the ``apply`` command for the provided profile.

    Args:
        args: Parsed CLI arguments for the ``apply`` subcommand.

    Returns:
        int: Exit code ``0`` when all items were submitted, ``3`` when any failed.

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
    events = iter_apply_events(_ensure_profile(profile_obj), mode)

    submitted = 0
    failed = 0
    if args.json:
        for event in events:
            _print_json(event)
            if event["event"] == "submitted":
                submitted += 1
            if event["event"] == "failed":
                failed += 1
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
                print(
                    "Submitted "
                    f"{event['id']} (confirmation: {confirmation})."
                )
            elif event["event"] == "failed":
                failed += 1
                reason = event.get("reason", {})
                print(f"Failed {event['id']}: {reason.get('message', 'Unknown reason')}")
        print(f"Session complete: {submitted} submitted, {failed} failed.")

    exit_code = 0 if failed == 0 else 3
    log_event("apply.complete", profile=profile_id, submitted=submitted, failed=failed)
    return exit_code


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a paused job from the persisted queues.

    Args:
        args: Parsed CLI arguments for the ``resume-job`` subcommand.

    Returns:
        int: Exit code ``0`` on success or ``4`` if the item could not be located.

    """
    try:
        payload = resume_job(args.id)
    except LookupError:
        payload = {"id": args.id, "status": "not_found", "resumed_from_step": 0}
        if args.json:
            _print_json(payload)
        else:
            print(f"Job {args.id} not found in queues.")
        log_event("resume.missing", item=args.id)
        return 4

    if args.json:
        _print_json(payload)
    else:
        print(f"Resumed job {payload['id']} from saved state.")
    log_event("resume.success", item=payload["id"], status=payload["status"])
    return 0


def iter_apply_events(
    profile: Profile,
    mode: str,
    *,
    fetch_form: Callable[[str], str] | None = None,
) -> Iterator[dict[str, object]]:
    """Yield apply events for streaming to the CLI.

    Args:
        profile: Active profile driving the application session.
        mode: ``"auto"`` or ``"supervised"`` mode indicator.
        fetch_form: Optional callable to retrieve HTML for a posting form.

    Yields:
        dict[str, object]: Event payloads following the apply contract schema.

    """
    profile = _ensure_profile(profile)
    queue = ApplicationQueue(profile.id)
    LeverBrowserOptions, LeverApplyAgent, BrowserSession = _load_browser_runtime()
    browser_options = LeverBrowserOptions.from_settings(profile=profile)
    agent = LeverApplyAgent(options=browser_options)
    submitted = 0
    failed = 0
    yield {"event": "start", "profile": profile.id}
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
            yield event_payload
        else:
            failed += 1
            queue.mark_failed(
                item.id,
                Reason(
                    code=reason.get("code", "failed"),
                    message=reason.get("message", "Failed"),
                ),
            )
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
    return {
        str(key): str(value)
        for key, value in raw.items()
        if value is not None
    }


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


def resume_job(job_id: str) -> dict[str, object]:
    """Resume a job by id, raising ``LookupError`` when absent.

    Args:
        job_id: Identifier returned from discovery/application queues.

    Returns:
        dict[str, object]: Payload describing resumed status and progress.

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
            try:
                queue.resume(job_id)
            except ValueError:
                item.status = ApplicationStatus.IN_PROGRESS
                item.last_updated_at = datetime.now(UTC)
                queue.update(item)
            return {
                "id": job_id,
                "status": ApplicationStatus.IN_PROGRESS.value,
                "resumed_from_step": 0,
            }
    raise LookupError(job_id)


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
        help=(
            "Override wait for upload success signals "
            "(AUTO_APPLY_RESUME_WAIT_TIMEOUT_SECONDS)"
        ),
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
    p_apply.set_defaults(func=cmd_apply)

    p_resume = sub.add_parser("resume-job", help="Resume a blocked job")
    p_resume.add_argument("id", help="Application item id")
    p_resume.add_argument("--json", action="store_true")
    p_resume.set_defaults(func=cmd_resume)

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
