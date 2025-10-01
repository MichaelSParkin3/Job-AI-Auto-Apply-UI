import json
import sys

import pytest

from src.orchestrator import main


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
    assert payload["id"] == "abc123"
    assert payload["status"] == "in_progress"
    assert err == ""

