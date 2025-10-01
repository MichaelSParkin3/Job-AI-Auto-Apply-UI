"""Contract tests for the `apply` CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from src.orchestrator import main


def run_cli(args: list[str]) -> tuple[int, str, str]:
    """Execute the CLI entry point and capture stdout/stderr."""
    from io import StringIO
    import contextlib

    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def load_schema() -> dict:
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo
        / "specs"
        / "001-as-a-job"
        / "contracts"
        / "schemas"
        / "apply-event.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_apply_human_output_summary(monkeypatch, tmp_path) -> None:
    """Human-mode apply run prints friendly summary text."""
    monkeypatch.setenv("JOB_APPLY_DATA_DIR", str(tmp_path))
    code, out, err = run_cli(["apply", "--profile", "front_end"])

    assert code == 0
    assert "Started apply session for profile" in out
    assert "Session complete" in out
    assert err == ""


def test_apply_json_stream_matches_schema(monkeypatch, tmp_path) -> None:
    """`apply --json` emits JSONL events that validate against schema."""
    monkeypatch.setenv("JOB_APPLY_DATA_DIR", str(tmp_path))
    code, out, err = run_cli(["apply", "--profile", "front_end", "--json"])

    assert code == 0
    schema = load_schema()
    events = [json.loads(line) for line in out.splitlines() if line.strip()]
    assert len(events) >= 2
    for event in events:
        validate(instance=event, schema=schema)
    assert err == ""
