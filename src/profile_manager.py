"""Profile management utilities for loading user configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import tomllib
from pydantic import BaseModel, Field, ValidationError, field_validator


class Profile(BaseModel):
    """Represents a user profile used to drive applications."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    resume_path: str = Field(min_length=1)
    defaults: Dict[str, Any] = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    prompts: Dict[str, str] = Field(default_factory=dict)
    user_data_dir: Optional[str] = None
    preferred_browser: Optional[str] = None

    @field_validator("keywords", mode="before")
    @classmethod
    def _flatten_keywords(cls, value: Any) -> list[str]:
        """Allow keywords to be stored as plain lists or nested `values` array."""
        if value is None:
            return []
        if isinstance(value, dict) and "values" in value:
            value = value["values"]
        if isinstance(value, (list, tuple)):
            flattened = [str(item).strip() for item in value if str(item).strip()]
            return flattened
        raise TypeError("keywords must be a list of strings or mapping with 'values'")

    @field_validator("prompts")
    @classmethod
    def _ensure_prompt_strings(cls, value: Dict[str, Any]) -> Dict[str, str]:
        return {key: str(text) for key, text in value.items()}

    def resolve_resume_path(self, base_dir: Path | None = None) -> Path:
        """Resolve the resume path relative to the provided base directory."""
        base = base_dir or Path.cwd()
        return (base / self.resume_path).expanduser().resolve()


class ProfileLoadError(RuntimeError):
    """Raised when a profile file cannot be found or validated."""


def _load_raw_profile(path: Path) -> Dict[str, Any]:
    """Load a raw profile configuration from the supplied path."""
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError as exc:  # pragma: no cover - handled by caller
        raise exc
    except (tomllib.TOMLDecodeError, OSError) as exc:  # pragma: no cover
        msg = f"Failed to parse profile file: {path}"
        raise ProfileLoadError(msg) from exc


def load_profile(profile_id: str, profiles_dir: Path | None = None) -> Profile:
    """Load a profile by id from the profiles directory."""
    directory = profiles_dir or Path("profiles")
    candidates = [directory / f"{profile_id}.toml", directory / f"{profile_id}.json"]

    for candidate in candidates:
        if candidate.exists():
            raw: Dict[str, Any]
            if candidate.suffix == ".json":
                import json

                raw = json.loads(candidate.read_text(encoding="utf-8"))
            else:
                raw = _load_raw_profile(candidate)
            data = dict(raw)
            if "id" not in data:
                data["id"] = profile_id
            elif data["id"] != profile_id:
                raise ProfileLoadError(
                    f"Profile id mismatch: requested '{profile_id}' but file defines '{data['id']}'"
                )
            try:
                return Profile.model_validate(data)
            except ValidationError as exc:
                msg = f"Profile validation failed for {candidate}"
                raise ProfileLoadError(msg) from exc

    raise ProfileLoadError(f"Profile '{profile_id}' not found in {directory}")
