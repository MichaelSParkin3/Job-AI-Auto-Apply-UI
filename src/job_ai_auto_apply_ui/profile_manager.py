"""Profile management utilities for the auto-apply assistant."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Profile",
    "ProfileNotFoundError",
    "InvalidProfileError",
    "load_profile",
    "profiles_root",
]


class ProfileNotFoundError(FileNotFoundError):
    """Raised when the requested profile file cannot be located."""


class InvalidProfileError(ValueError):
    """Raised when a profile file is missing required fields."""


@dataclass(slots=True)
class Profile:
    """In-memory representation of a user profile."""

    id: str
    name: str
    resume_path: Path
    defaults: Mapping[str, str]
    keywords: Mapping[str, Iterable[str]]
    prompts: Mapping[str, str]
    user_data_dir: Path | None = None
    preferred_browser: str | None = None

    def discovery_terms(self) -> list[str]:
        """Flatten keyword categories into a list of discovery search terms."""
        terms: list[str] = []
        for values in self.keywords.values():
            for value in values:
                if value and isinstance(value, str):
                    terms.append(value.strip())
        return [term for term in terms if term]

    def resolve_resume_path(self, base: Path | None = None) -> Path:
        """Return an absolute path to the resume file, preserving relative semantics."""
        if self.resume_path.is_absolute():
            return self.resume_path
        base_dir = base or Path.cwd()
        return (base_dir / self.resume_path).resolve()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> Profile:
        """Create a profile from parsed TOML mapping."""
        try:
            profile_id = str(payload["id"])
            name = str(payload.get("name", profile_id.title()))
            resume_path = Path(str(payload["resume_path"]))
        except KeyError as exc:  # pragma: no cover - validated paths only
            raise InvalidProfileError(f"Profile missing required field: {exc.args[0]}") from exc

        defaults = _coerce_str_mapping(payload.get("defaults", {}))
        keywords_raw = payload.get("keywords", {})
        keywords: dict[str, list[str]] = {
            key: [str(item) for item in value if str(item).strip()]
            for key, value in _coerce_list_mapping(keywords_raw).items()
        }
        prompts = _coerce_str_mapping(payload.get("prompts", {}))
        user_data_dir = _maybe_path(payload.get("user_data_dir"))
        preferred_browser = _maybe_str(payload.get("preferred_browser"))

        return cls(
            id=profile_id,
            name=name,
            resume_path=resume_path,
            defaults=defaults,
            keywords=keywords,
            prompts=prompts,
            user_data_dir=user_data_dir,
            preferred_browser=preferred_browser,
        )


def profiles_root(base: Path | None = None) -> Path:
    """Return the directory containing profile files."""
    if base:
        return base
    env_override = os.getenv("AUTO_APPLY_PROFILES_DIR")
    if env_override:
        return Path(env_override).expanduser().resolve()
    return Path.cwd() / "profiles"


def load_profile(profile_id: str, base_dir: Path | None = None) -> Profile:
    """Load a profile by id from the configured profiles directory."""
    directory = profiles_root(base_dir)
    candidate = directory / f"{profile_id}.toml"
    if not candidate.exists():
        raise ProfileNotFoundError(f"Profile '{profile_id}' not found at {candidate}")

    data = tomllib.loads(candidate.read_text(encoding="utf-8"))
    try:
        mapping: Mapping[str, object] = data
    except Exception as exc:  # pragma: no cover - tomllib guarantees dict
        raise InvalidProfileError(f"Invalid profile TOML for '{profile_id}'") from exc

    profile = Profile.from_mapping(mapping)
    return profile


def _coerce_str_mapping(raw: object) -> Mapping[str, str]:
    if not isinstance(raw, MutableMapping):
        return {}
    return {str(key): str(value) for key, value in raw.items() if value is not None}


def _coerce_list_mapping(raw: object) -> Mapping[str, list[str]]:
    if not isinstance(raw, MutableMapping):
        return {}
    result: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, Iterable) and not isinstance(value, str | bytes):
            result[str(key)] = [str(item) for item in value if item is not None]
    return result


def _maybe_path(raw: object) -> Path | None:
    if not raw:
        return None
    try:
        return Path(str(raw))
    except TypeError:  # pragma: no cover - defensive
        return None


def _maybe_str(raw: object) -> str | None:
    if raw is None:
        return None
    return str(raw)
