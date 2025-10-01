"""Contract tests for the `resume-job` CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from src.application_queue import ApplicationQueue, ApplicationStatus, JobDetails
from src.orchestrator import main


def run_cli(args: list[str]) -> tuple[int, str, str]:
    """Run CLI with args and capture stdout/stderr."""
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
        / "resume-job.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_resume_job_json_contract(tmp_path, monkeypatch) -> None:
    """`resume-job --json` returns schema-compliant payload and exit code 0."""
    monkeypatch.setenv("JOB_APPLY_DATA_DIR", str(tmp_path))
    queue = ApplicationQueue("front_end")
    result = queue.enqueue(
        url="https://example.com/job",
        company="Example Co",
        title="QA Engineer",
        details=JobDetails(location="Remote"),
    )
    queue.update_item(result.item.id, status=ApplicationStatus.IN_PROGRESS)

    code, out, err = run_cli([
        "resume-job",
        result.item.id,
        "--profile",
        "front_end",
        "--json",
    ])

    assert code == 0
    payload = json.loads(out)
    validate(instance=payload, schema=load_schema())
    assert payload["id"] == result.item.id
    assert err == ""
