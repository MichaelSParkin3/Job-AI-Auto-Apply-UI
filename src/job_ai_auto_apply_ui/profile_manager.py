"""Profile management utilities for the auto-apply assistant."""

from __future__ import annotations

import os
import tomllib
import tomli_w
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Profile",
    "ProfileNotFoundError",
    "InvalidProfileError",
    "load_profile",
    "save_profile",
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
    experience: list[Mapping[str, object]] | None = None
    search_query: str | None = None

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
        search_query = _maybe_str(payload.get("search_query"))

        # Load experience array from [[experience]] sections
        experience_raw = payload.get("experience", [])
        experience: list[Mapping[str, object]] = []
        if isinstance(experience_raw, list):
            experience = [
                {key: value for key, value in item.items() if isinstance(item, MutableMapping)}
                for item in experience_raw
                if isinstance(item, MutableMapping)
            ]

        return cls(
            id=profile_id,
            name=name,
            resume_path=resume_path,
            defaults=defaults,
            keywords=keywords,
            prompts=prompts,
            user_data_dir=user_data_dir,
            preferred_browser=preferred_browser,
            experience=experience if experience else None,
            search_query=search_query,
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


def save_profile(
    profile_id: str,
    profile_data: Mapping[str, object],
    base_dir: Path | None = None,
) -> Path:
    """Save a profile to disk as a TOML file.

    Args:
        profile_id: Profile identifier (becomes filename)
        profile_data: Profile data mapping with keys like id, name, resume_path, etc.
        base_dir: Directory to save to (defaults to profiles root)

    Returns:
        Path to the saved profile file

    Raises:
        InvalidProfileError: If required fields are missing or invalid
        OSError: If file cannot be written
    """
    # Validate required fields
    if not profile_data.get("id"):
        raise InvalidProfileError("Profile must have 'id' field")
    if not profile_data.get("name"):
        raise InvalidProfileError("Profile must have 'name' field")
    if not profile_data.get("resume_path"):
        raise InvalidProfileError("Profile must have 'resume_path' field")

    directory = profiles_root(base_dir)
    directory.mkdir(parents=True, exist_ok=True)

    # Build TOML structure
    output: dict[str, object] = {
        "id": str(profile_data["id"]),
        "name": str(profile_data["name"]),
        "resume_path": str(profile_data["resume_path"]),
    }

    # Add optional fields
    if profile_data.get("preferred_browser"):
        output["preferred_browser"] = str(profile_data["preferred_browser"])
    if profile_data.get("user_data_dir"):
        output["user_data_dir"] = str(profile_data["user_data_dir"])
    if profile_data.get("search_query"):
        output["search_query"] = str(profile_data["search_query"])

    # Add defaults mapping
    if profile_data.get("defaults"):
        output["defaults"] = _coerce_str_mapping(profile_data["defaults"])

    # Add keywords mapping
    if profile_data.get("keywords"):
        output["keywords"] = _coerce_list_mapping(profile_data["keywords"])

    # Add prompts mapping
    if profile_data.get("prompts"):
        output["prompts"] = _coerce_str_mapping(profile_data["prompts"])

    # Add experience array
    if profile_data.get("experience"):
        exp_raw = profile_data["experience"]
        if isinstance(exp_raw, list):
            experience_list: list[dict[str, object]] = []
            for item in exp_raw:
                if isinstance(item, MutableMapping):
                    # Convert each experience item
                    exp_item: dict[str, object] = {
                        "company": str(item.get("company", "")),
                        "role": str(item.get("role", "")),
                        "dates": str(item.get("dates", "")),
                    }
                    if item.get("location"):
                        exp_item["location"] = str(item["location"])
                    if item.get("context"):
                        exp_item["context"] = str(item["context"])

                    # Highlights and tech_stack as lists
                    highlights = item.get("highlights", [])
                    if isinstance(highlights, list):
                        exp_item["highlights"] = [str(h) for h in highlights if h]
                    tech_stack = item.get("tech_stack", [])
                    if isinstance(tech_stack, list):
                        exp_item["tech_stack"] = [str(t) for t in tech_stack if t]

                    # Metrics as mapping
                    metrics = item.get("metrics", {})
                    if isinstance(metrics, MutableMapping):
                        exp_item["metrics"] = {
                            str(k): str(v) for k, v in metrics.items() if v
                        }

                    experience_list.append(exp_item)
            if experience_list:
                output["experience"] = experience_list

    # Write TOML file
    candidate = directory / f"{profile_id}.toml"
    toml_content = tomli_w.dumps(output)
    candidate.write_text(toml_content, encoding="utf-8")

    return candidate
