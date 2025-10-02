import json
from pathlib import Path

import pytest
from jsonschema import validate

from job_ai_auto_apply_ui.orchestrator import main


def run_cli(args):
    """Run the CLI main with given args and capture output."""
    from io import StringIO
    import contextlib

    buf_out, buf_err = StringIO(), StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        code = main(args)
    return code, buf_out.getvalue(), buf_err.getvalue()


def test_discover_json_contract_no_results():
    code, out, err = run_cli(["discover", "--profile", "dev", "--json"]) 
    assert code == 2
    payload = json.loads(out)
    # Validate against JSON schema
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo
        / "specs"
        / "001-as-a-job"
        / "contracts"
        / "schemas"
        / "discover.schema.json"
    )
    discover_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=payload, schema=discover_schema)
    assert isinstance(payload, dict)
    assert "items" in payload and isinstance(payload["items"], list)
    assert err == ""


def test_apply_human_mode_success():
    code, out, err = run_cli(["apply", "--profile", "dev"]) 
    assert code == 0
    assert "Started apply session" in out
    assert err == ""


def test_resume_job_json_contract():
    code, out, err = run_cli(["resume-job", "abc123", "--json"]) 
    assert code == 0
    payload = json.loads(out)
    # Validate against JSON schema
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo
        / "specs"
        / "001-as-a-job"
        / "contracts"
        / "schemas"
        / "resume-job.schema.json"
    )
    resume_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=payload, schema=resume_schema)
    assert payload["id"] == "abc123"
    assert payload["status"] == "in_progress"
    assert err == ""


def test_apply_json_event_schema():
    code, out, err = run_cli(["apply", "--profile", "dev", "--json"]) 
    assert code == 0
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert len(lines) >= 2  # start and end
    repo = Path(__file__).resolve().parents[2]
    schema_path = (
        repo
        / "specs"
        / "001-as-a-job"
        / "contracts"
        / "schemas"
        / "apply-event.schema.json"
    )
    event_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for ln in lines:
        evt = json.loads(ln)
        validate(instance=evt, schema=event_schema)
    assert err == ""
