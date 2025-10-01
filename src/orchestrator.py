"""CLI Orchestrator for Lever Auto‑Apply Assistant.

Provides contract-aligned commands: discover, apply, resume-job.
Outputs human-readable text by default, with optional --json mode.

This is a minimal MVP stub to enable contract tests and iteration.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def cmd_discover(args: argparse.Namespace) -> int:
    """Discover Lever postings via Google (stub).

    Args:
      args: Parsed CLI arguments with profile, window, cap, json.

    Returns:
      Exit code. 2 indicates no results (not an error for MVP stub).
    """
    result = {"items": []}
    if args.json:
        _print_json(result)
    else:
        print("No new postings discovered in the selected window.")
    return 2


def cmd_apply(args: argparse.Namespace) -> int:
    """Apply to queued postings for a profile (stub).

    Args:
      args: Parsed CLI arguments with profile, mode, json.

    Returns:
      Exit code 0 for successful run (even if no items in MVP stub).
    """
    events: List[Dict[str, Any]] = [
        {"event": "start", "profile": args.profile},
        {"event": "end", "summary": {"submitted": 0, "failed": 0}},
    ]
    if args.json:
        for ev in events:
            _print_json(ev)
    else:
        print(f"Started apply session for profile '{args.profile}'.")
        print("No items in queue. Session complete.")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a job from saved state (stub)."""
    payload = {"id": args.id, "status": "in_progress", "resumed_from_step": 0}
    if args.json:
        _print_json(payload)
    else:
        print(f"Resumed job {args.id} from saved state.")
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


if __name__ == "__main__":
    sys.exit(main())

