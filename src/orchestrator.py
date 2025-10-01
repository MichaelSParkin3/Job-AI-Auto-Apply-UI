"""CLI Orchestrator for Lever Auto‑Apply Assistant."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

from .application_queue import ApplicationQueue, ApplicationStatus, Artifacts
from .job_discovery import discover_jobs
from .llm import load_llm_config
from .profile_manager import Profile, load_profile
from .telemetry import bind_timeline, log_event


def _print_json(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def cmd_discover(args: argparse.Namespace) -> int:
    """Execute the `discover` command and emit queue updates."""
    profile = load_profile(args.profile)
    window_hours = _parse_window_hours(args.window)
    queue = ApplicationQueue(profile.id)
    log_event("discover.start", profile=profile.id, window_hours=window_hours, cap=args.cap)
    items = discover_jobs(profile=profile, window_hours=window_hours, cap=args.cap)
    accepted = queue.enqueue(items)
    payload = {"items": [item.to_contract_dict() for item in accepted]}

    if args.json:
        _print_json(payload)
    else:
        if accepted:
            print(
                "Discovered "
                f"{len(accepted)} new postings for profile '{profile.name}'."
            )
        else:
            print("No new postings discovered in the selected window.")
    log_event("discover.complete", profile=profile.id, new=len(accepted))
    return 0 if accepted else 2


def cmd_apply(args: argparse.Namespace) -> int:
    """Execute the `apply` command for the provided profile."""
    profile = load_profile(args.profile)
    mode = "auto" if args.auto else "supervised"
    llm_config = load_llm_config()
    if getattr(args, "llm_provider", None):
        llm_config.provider = args.llm_provider
    if getattr(args, "llm_model", None):
        llm_config.model = args.llm_model
    log_event("apply.start", profile=profile.id, mode=mode)
    log_event(
        "apply.llm_config",
        provider=llm_config.provider,
        model=llm_config.model,
    )
    events = iter_apply_events(profile, mode)

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
        print(f"Starting apply session for '{profile.name}' in {mode} mode.")
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
    log_event("apply.complete", profile=profile.id, submitted=submitted, failed=failed)
    return exit_code


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a paused job from the persisted queues."""
    try:
        payload = resume_job(args.id)
    except LookupError:
        payload = {"id": args.id, "status": "not_found", "resumed_from_step": None}
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


def iter_apply_events(profile: Profile, mode: str) -> Iterator[dict[str, object]]:
    """Yield apply events for streaming to the CLI."""
    queue = ApplicationQueue(profile.id)
    submitted = 0
    failed = 0
    yield {"event": "start", "profile": profile.id, "mode": mode}
    pending = queue.pending()
    log_event("apply.pending", profile=profile.id, count=len(pending))
    for item in pending:
        queue.resume(item.id)
        timeline = bind_timeline("apply", item=item.id)
        timeline.info("item.start")
        yield {"event": "item", "id": item.id, "status": ApplicationStatus.IN_PROGRESS.value}
        confirmation = Artifacts(confirmation_text="submitted (placeholder)")
        queue.mark_submitted(item.id, confirmation)
        submitted += 1
        timeline.info("item.submitted", confirmation_text=confirmation.confirmation_text)
        yield {
            "event": "submitted",
            "id": item.id,
            "confirmation_text": confirmation.confirmation_text,
        }
    yield {"event": "end", "summary": {"submitted": submitted, "failed": failed}}


def resume_job(job_id: str) -> dict[str, object]:
    """Resume a job by id, raising LookupError when absent."""
    queue_dir = Path.cwd() / "data" / "queues"
    queue_dir.mkdir(parents=True, exist_ok=True)
    for queue_path in queue_dir.glob("*.json"):
        profile_id = queue_path.stem
        queue = ApplicationQueue(profile_id)
        item = queue.get(job_id)
        if item:
            queue.resume(job_id)
            return {
                "id": job_id,
                "status": ApplicationStatus.IN_PROGRESS.value,
                "resumed_from_step": 0,
            }
    raise LookupError(job_id)


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI argument parser."""
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
    p_apply.set_defaults(func=cmd_apply)

    p_resume = sub.add_parser("resume-job", help="Resume a blocked job")
    p_resume.add_argument("id", help="Application item id")
    p_resume.add_argument("--json", action="store_true")
    p_resume.set_defaults(func=cmd_resume)

    return parser


def _parse_window_hours(value: str) -> int:
    """Parse shorthand duration strings into hours."""
    value = value.strip().lower()
    if value.endswith("h"):
        return max(1, int(value[:-1]))
    if value.endswith("d"):
        return max(1, int(value[:-1]) * 24)
    if value.endswith("w"):
        return max(1, int(value[:-1]) * 24 * 7)
    return max(1, int(value))


def main(argv: Iterable[str] | None = None) -> int:
    """Entry point for the auto-apply CLI."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
