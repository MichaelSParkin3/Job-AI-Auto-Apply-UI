"""Contract tests for the `discover` CLI command."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate

from job_ai_auto_apply_ui.orchestrator import main


@dataclass
class _FakeItem:
    data: dict[str, Any]

    def to_contract_dict(self) -> dict[str, Any]:
        return self.data


def _run_cli(args: Iterable[str]) -> tuple[int, str, str]:
    """Run the CLI with the provided arguments and capture stdio."""
    import contextlib
    from io import StringIO

    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(list(args))
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.fixture()
def discover_schema() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    schema_path = (
        repo_root / "specs" / "001-as-a-job" / "contracts" / "schemas" / "discover.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_discover_json_success(
    monkeypatch: pytest.MonkeyPatch, discover_schema: dict[str, Any]
) -> None:
    """Successful discovery returns JSON that matches the schema and exit code 0."""
    fake_items: list[_FakeItem] = [
        _FakeItem(
            {
                "id": "item-1",
                "url": "https://jobs.lever.co/example/1",
                "company": "Example",
                "title": "Front-End Engineer",
                "discovered_at": "2025-10-01T12:00:00+00:00",
            }
        ),
    ]

    def fake_load_profile(profile_id: str) -> dict[str, Any]:
        assert profile_id == "front_end"
        return {"id": profile_id, "name": "Front End"}

    def fake_discover(profile: dict[str, Any], window_hours: int, cap: int) -> list[_FakeItem]:
        assert profile["id"] == "front_end"
        assert window_hours == 24
        assert cap == 5
        return fake_items

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.job_discovery.discover_jobs", fake_discover
    )

    code, out, err = _run_cli(
        ["discover", "--profile", "front_end", "--window", "24h", "--cap", "5", "--json"]
    )

    assert code == 0
    payload = json.loads(out)
    validate(instance=payload, schema=discover_schema)
    assert payload["items"] == [item.data for item in fake_items]
    assert err == ""


def test_discover_json_no_results(
    monkeypatch: pytest.MonkeyPatch, discover_schema: dict[str, Any]
) -> None:
    """When no items are discovered the command exits with code 2."""

    def fake_load_profile(profile_id: str) -> dict[str, Any]:
        return {"id": profile_id, "name": profile_id.title()}

    def fake_discover(profile: dict[str, Any], window_hours: int, cap: int) -> list[_FakeItem]:
        return []

    monkeypatch.setattr(
        "job_ai_auto_apply_ui.profile_manager.load_profile", fake_load_profile
    )
    monkeypatch.setattr(
        "job_ai_auto_apply_ui.job_discovery.discover_jobs", fake_discover
    )

    code, out, err = _run_cli(["discover", "--profile", "front_end", "--json"])

    assert code == 2
    payload = json.loads(out)
    validate(instance=payload, schema=discover_schema)
    assert payload["items"] == []
    assert err == ""
