"""CLI orchestrator wiring discovery, apply, and resume commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

from . import job_discovery
from .application_queue import ApplicationQueue, ApplicationStatus
from .profile_manager import ProfileLoadError, load_profile


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def cmd_discover(args: argparse.Namespace) -> int:
    """Discover Lever postings via Google and enqueue new items."""
    try:
        profile = load_profile(args.profile)
    except ProfileLoadError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    window_hours = _parse_window(args.window)
    query_url = job_discovery.build_search_url(
        keywords=profile.keywords or [profile.name],
        window_hours=window_hours,
        cap=args.cap,
    )

    queue = ApplicationQueue(profile.id)
    # Placeholder: actual scraping occurs in later implementation phases.
    items: List[Dict[str, Any]] = []

    if args.json:
        _print_json({"items": items})
    else:
        if items:
            print(f"Discovered {len(items)} new postings. Enqueued for profile '{profile.id}'.")
        else:
            print("No new postings discovered in the selected window.")
            print(f"Search URL: {query_url}")

    return 0 if items else 2


def cmd_apply(args: argparse.Namespace) -> int:
    """Apply to queued postings for a profile."""
    try:
        profile = load_profile(args.profile)
    except ProfileLoadError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    queue = ApplicationQueue(profile.id)
    items = queue.list_items()
    events: List[Dict[str, Any]] = [
        {"event": "start", "profile": profile.id},
    ]

    submitted = 0
    failed = 0

    for item in items:
        queue.update_item(item.id, status=ApplicationStatus.IN_PROGRESS)
        events.append({"event": "item", "id": item.id, "status": ApplicationStatus.IN_PROGRESS.value})
        # Placeholder for actual browser automation and LLM answers.
        queue.update_item(item.id, status=ApplicationStatus.SUBMITTED)
        events.append({"event": "submitted", "id": item.id})
        submitted += 1

    events.append({"event": "end", "summary": {"submitted": submitted, "failed": failed}})

    if args.json:
        for event in events:
            _print_json(event)
    else:
        print(f"Started apply session for profile '{profile.id}'.")
        if submitted:
            print(f"Submitted {submitted} application(s).")
        else:
            print("No items in queue. Session complete.")

    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a job from saved state."""
    queue = ApplicationQueue(args.profile)
    item = queue.get(args.id)
    if item is None:
        payload = {"id": args.id, "status": "not_found"}
        if args.json:
            _print_json(payload)
        else:
            print(f"No saved job found with id {args.id}.")
        return 4

    payload = {
        "id": item.id,
        "status": item.status.value,
        "resumed_from_step": 0,
    }
    if args.json:
        _print_json(payload)
    else:
        print(f"Resumed job {item.id} from saved state.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="auto-apply",
        description=(
            "Lever Auto‑Apply Assistant (MVP). "
            "Use --json for machine-readable outputs."
        ),
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
    p_apply.set_defaults(func=cmd_apply)

    p_resume = sub.add_parser("resume-job", help="Resume a blocked job")
    p_resume.add_argument("id", help="Application item id")
    p_resume.add_argument("--profile", required=True, help="Profile identifier")
    p_resume.add_argument("--json", action="store_true")
    p_resume.set_defaults(func=cmd_resume)

    return parser


def main(argv: List[str] | None = None) -> int:
    """Entry point for CLI.

    Args:
      argv: Optional list of arguments. Defaults to sys.argv[1:].

    Returns:
      Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _parse_window(value: str) -> int:
    """Convert CLI window value (e.g., 24h, 7d) into hours."""
    value = value.strip().lower()
    if value.endswith("h"):
        return max(1, int(value[:-1]))
    if value.endswith("d"):
        return max(1, int(value[:-1]) * 24)
    return max(1, int(value))


if __name__ == "__main__":
    sys.exit(main())

