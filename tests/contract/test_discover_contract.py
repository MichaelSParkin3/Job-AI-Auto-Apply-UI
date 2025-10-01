"""Contract tests for the `discover` CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from src.orchestrator import main


def run_cli(args: list[str]) -> tuple[int, str, str]:
    """Execute the CLI and capture stdout/stderr text."""
    from io import StringIO
    import contextlib

    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def load_schema(name: str) -> dict:
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo
        / "specs"
        / "001-as-a-job"
        / "contracts"
        / "schemas"
        / name
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_discover_contract_no_results_json_output(monkeypatch, tmp_path) -> None:
    """`discover --json` returns schema-compliant payload and exit code 2."""
    monkeypatch.setenv("JOB_APPLY_DATA_DIR", str(tmp_path))
    code, out, err = run_cli(["discover", "--profile", "front_end", "--json"])

    assert code == 2
    payload = json.loads(out)
    validate(instance=payload, schema=load_schema("discover.schema.json"))
    assert payload["items"] == []
    assert err == ""
