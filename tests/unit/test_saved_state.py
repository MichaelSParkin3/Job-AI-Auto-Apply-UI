"""Unit tests for saved_state read/write helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_ai_auto_apply_ui.saved_state import read_pre_state, write_pre_state


@pytest.fixture()
def sample_saved_state() -> dict:
    """Create a sample SavedState v1 payload."""
    return {
        "version": 1,
        "captured_at": "2024-01-15T10:30:00Z",
        "profile_id": "test-profile",
        "item_id": "01HXYZ123",
        "url": "https://jobs.example.com/posting",
        "apply_url": "https://jobs.example.com/apply/posting",
        "plan": {
            "resume_input": "#resume-upload",
            "contact_fields": {
                "name": "#name-input",
                "email": "#email-input",
                "phone": "#phone-input",
            },
            "link_fields": {
                "linkedin": "#linkedin-input",
                "github": "#github-input",
            },
            "submit_button": "button#btn-submit",
            "captcha_selector": "div#h-captcha",
        },
        "values": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-123-4567",
            "linkedin": "https://linkedin.com/in/johndoe",
        },
        "labels": {
            "company": "Example Corp",
            "title": "Software Engineer",
        },
    }


@pytest.fixture()
def sample_state_without_labels() -> dict:
    """Create a SavedState v1 payload without optional labels."""
    return {
        "version": 1,
        "captured_at": "2024-01-15T10:30:00Z",
        "profile_id": "test-profile",
        "item_id": "01HXYZ123",
        "url": "https://jobs.example.com/posting",
        "apply_url": "https://jobs.example.com/apply/posting",
        "plan": {
            "resume_input": "#resume-upload",
            "contact_fields": {"name": "#name-input"},
            "link_fields": {},
            "submit_button": "button#btn-submit",
            "captcha_selector": None,
        },
        "values": {"name": "John Doe"},
    }


class TestWritePreState:
    """Test write_pre_state() functionality."""

    def test_creates_parent_directories(self, tmp_path: Path, sample_saved_state: dict) -> None:
        """write_pre_state should create parent directories if missing."""
        nested_path = tmp_path / "artifacts" / "profile123" / "item456" / "pre.json"
        assert not nested_path.parent.exists()

        write_pre_state(nested_path, sample_saved_state)

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_writes_valid_json(self, tmp_path: Path, sample_saved_state: dict) -> None:
        """write_pre_state should write valid JSON with proper encoding."""
        file_path = tmp_path / "pre.json"

        write_pre_state(file_path, sample_saved_state)

        assert file_path.exists()
        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed == sample_saved_state

    def test_includes_all_required_v1_fields(
        self, tmp_path: Path, sample_saved_state: dict
    ) -> None:
        """Written JSON should include all required v1 schema fields."""
        file_path = tmp_path / "pre.json"

        write_pre_state(file_path, sample_saved_state)

        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)

        assert "version" in parsed
        assert "captured_at" in parsed
        assert "profile_id" in parsed
        assert "item_id" in parsed
        assert "url" in parsed
        assert "apply_url" in parsed
        assert "plan" in parsed
        assert "values" in parsed

    def test_handles_unicode_correctly(self, tmp_path: Path) -> None:
        """write_pre_state should handle unicode characters correctly."""
        file_path = tmp_path / "pre.json"
        payload = {
            "version": 1,
            "captured_at": "2024-01-15T10:30:00Z",
            "profile_id": "test",
            "item_id": "123",
            "url": "https://example.com",
            "apply_url": "https://example.com/apply",
            "plan": {"resume_input": "#resume"},
            "values": {"name": "Müller François 日本語"},
        }

        write_pre_state(file_path, payload)

        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["values"]["name"] == "Müller François 日本語"

    def test_formats_json_with_indentation(self, tmp_path: Path, sample_saved_state: dict) -> None:
        """write_pre_state should format JSON with indentation for readability."""
        file_path = tmp_path / "pre.json"

        write_pre_state(file_path, sample_saved_state)

        content = file_path.read_text(encoding="utf-8")
        # Indented JSON should have newlines and spaces
        assert "\n" in content
        assert "  " in content  # 2-space indentation


class TestReadPreState:
    """Test read_pre_state() functionality."""

    def test_reads_existing_file_correctly(self, tmp_path: Path, sample_saved_state: dict) -> None:
        """read_pre_state should read and parse existing file correctly."""
        file_path = tmp_path / "pre.json"
        file_path.write_text(json.dumps(sample_saved_state), encoding="utf-8")

        result = read_pre_state(file_path)

        assert result == sample_saved_state

    def test_returns_proper_dict_structure(self, tmp_path: Path, sample_saved_state: dict) -> None:
        """read_pre_state should return a dict with expected structure."""
        file_path = tmp_path / "pre.json"
        file_path.write_text(json.dumps(sample_saved_state), encoding="utf-8")

        result = read_pre_state(file_path)

        assert isinstance(result, dict)
        assert result["version"] == 1
        assert result["profile_id"] == "test-profile"
        assert isinstance(result["plan"], dict)
        assert isinstance(result["values"], dict)

    def test_raises_filenotfounderror_when_missing(self, tmp_path: Path) -> None:
        """read_pre_state should raise FileNotFoundError when file doesn't exist."""
        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            read_pre_state(file_path)

    def test_raises_jsondecodeerror_when_corrupt(self, tmp_path: Path) -> None:
        """read_pre_state should raise JSONDecodeError when JSON is invalid."""
        file_path = tmp_path / "corrupt.json"
        file_path.write_text("{ invalid json }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            read_pre_state(file_path)

    def test_handles_unicode_correctly(self, tmp_path: Path) -> None:
        """read_pre_state should handle unicode characters correctly."""
        file_path = tmp_path / "pre.json"
        payload = {
            "version": 1,
            "values": {"name": "Müller François 日本語"},
        }
        file_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        result = read_pre_state(file_path)

        assert result["values"]["name"] == "Müller François 日本語"


class TestOptionalLabels:
    """Test handling of optional labels field."""

    def test_write_with_labels_field(self, tmp_path: Path, sample_saved_state: dict) -> None:
        """write_pre_state should include labels field when present."""
        file_path = tmp_path / "pre.json"

        write_pre_state(file_path, sample_saved_state)

        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "labels" in parsed
        assert parsed["labels"]["company"] == "Example Corp"
        assert parsed["labels"]["title"] == "Software Engineer"

    def test_write_without_labels_field(
        self, tmp_path: Path, sample_state_without_labels: dict
    ) -> None:
        """write_pre_state should work when labels field is absent."""
        file_path = tmp_path / "pre.json"

        write_pre_state(file_path, sample_state_without_labels)

        content = file_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert "labels" not in parsed

    def test_read_both_variants_successfully(
        self,
        tmp_path: Path,
        sample_saved_state: dict,
        sample_state_without_labels: dict,
    ) -> None:
        """read_pre_state should handle both with and without labels."""
        # With labels
        file_with_labels = tmp_path / "with_labels.json"
        file_with_labels.write_text(json.dumps(sample_saved_state), encoding="utf-8")

        result_with = read_pre_state(file_with_labels)
        assert "labels" in result_with
        assert result_with["labels"]["company"] == "Example Corp"

        # Without labels
        file_without_labels = tmp_path / "without_labels.json"
        file_without_labels.write_text(json.dumps(sample_state_without_labels), encoding="utf-8")

        result_without = read_pre_state(file_without_labels)
        assert "labels" not in result_without


class TestRoundTrip:
    """Test that write followed by read preserves data."""

    def test_round_trip_preserves_all_data(self, tmp_path: Path, sample_saved_state: dict) -> None:
        """Data should be preserved through write → read cycle."""
        file_path = tmp_path / "pre.json"

        write_pre_state(file_path, sample_saved_state)
        result = read_pre_state(file_path)

        assert result == sample_saved_state

    def test_round_trip_without_labels(
        self, tmp_path: Path, sample_state_without_labels: dict
    ) -> None:
        """Round-trip should work without labels field."""
        file_path = tmp_path / "pre.json"

        write_pre_state(file_path, sample_state_without_labels)
        result = read_pre_state(file_path)

        assert result == sample_state_without_labels
