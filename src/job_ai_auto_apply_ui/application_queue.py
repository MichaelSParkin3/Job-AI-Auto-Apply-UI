"""Persistent application queue management."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable, Iterator, MutableMapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from .telemetry import log_event

__all__ = [
    "ApplicationStatus",
    "Reason",
    "Artifacts",
    "JobDetails",
    "ApplicationItem",
    "ApplicationQueue",
    "new_ulid",
]


class ApplicationStatus(str, Enum):
    """States for an application item."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    CAPTCHA_BLOCKED = "captcha_blocked"
    SUBMITTED = "submitted"
    FAILED = "failed"


@dataclass(slots=True)
class Reason:
    """Failure or status reason metadata."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Convert the reason into a serialisable dictionary.

        Returns:
            dict[str, str]: Mapping with ``code`` and ``message`` keys.

        """
        return {"code": self.code, "message": self.message}


@dataclass(slots=True)
class Artifacts:
    """Captured artifacts for an application run."""

    dom_snapshot_path: str | None = None
    screenshot_path: str | None = None
    video_path: str | None = None
    har_path: str | None = None
    confirmation_text: str | None = None
    confirmation_id: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Return a dictionary representation of the captured artifacts.

        Returns:
            dict[str, str | None]: Mapping of artifact fields to their values.

        """
        return {
            "dom_snapshot_path": self.dom_snapshot_path,
            "screenshot_path": self.screenshot_path,
            "video_path": self.video_path,
            "har_path": self.har_path,
            "confirmation_text": self.confirmation_text,
            "confirmation_id": self.confirmation_id,
        }

    @classmethod
    def from_dict(cls, data: MutableMapping[str, str | None]) -> Artifacts:
        """Build an :class:`Artifacts` instance from a dictionary mapping.

        Args:
            data: Mapping containing artifact paths and confirmation metadata.

        Returns:
            Artifacts: Parsed artifact container.

        """
        return cls(
            dom_snapshot_path=data.get("dom_snapshot_path"),
            screenshot_path=data.get("screenshot_path"),
            video_path=data.get("video_path"),
            har_path=data.get("har_path"),
            confirmation_text=data.get("confirmation_text"),
            confirmation_id=data.get("confirmation_id"),
        )


@dataclass(slots=True)
class JobDetails:
    """Normalized details extracted from a Lever posting."""

    location: str | None = None
    work_model: str = "unknown"
    employment_type: str = "unknown"
    department: str | None = None
    posting_date: datetime | None = None
    compensation: dict[str, object] | None = None
    posting_excerpt: str | None = None
    posting_text: str | None = None
    tech_tags: list[str] = field(default_factory=list)
    source_query: str | None = None
    source_rank: int | None = None
    apply_url: str | None = None
    closed: bool = False
    extracted_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialise job details to a JSON-friendly mapping.

        Returns:
            dict[str, object]: Mapping containing location, posting metadata, and
            auxiliary information for persistence.

        """
        payload: dict[str, object] = {
            "location": self.location,
            "work_model": self.work_model,
            "employment_type": self.employment_type,
            "department": self.department,
            "posting_date": _dt_to_iso(self.posting_date),
            "compensation": self.compensation,
            "posting_excerpt": self.posting_excerpt,
            "posting_text": self.posting_text,
            "tech_tags": list(self.tech_tags),
            "source_query": self.source_query,
            "source_rank": self.source_rank,
            "apply_url": self.apply_url,
            "closed": self.closed,
            "extracted_at": _dt_to_iso(self.extracted_at),
        }
        return payload

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> JobDetails:
        """Create :class:`JobDetails` from a persisted mapping.

        Args:
            data: Mapping with stored job detail fields.

        Returns:
            JobDetails: Reconstructed details instance.

        """
        return cls(
            location=_maybe_str(data.get("location")),
            work_model=_maybe_str(data.get("work_model")) or "unknown",
            employment_type=_maybe_str(data.get("employment_type")) or "unknown",
            department=_maybe_str(data.get("department")),
            posting_date=_maybe_datetime(data.get("posting_date")),
            compensation=data.get("compensation"),
            posting_excerpt=_maybe_str(data.get("posting_excerpt")),
            posting_text=_maybe_str(data.get("posting_text")),
            tech_tags=[str(tag) for tag in data.get("tech_tags", []) if tag is not None],
            source_query=_maybe_str(data.get("source_query")),
            source_rank=_maybe_int(data.get("source_rank")),
            apply_url=_maybe_str(data.get("apply_url")),
            closed=bool(data.get("closed", False)),
            extracted_at=_maybe_datetime(data.get("extracted_at")),
        )


@dataclass(slots=True)
class ApplicationItem:
    """Queue item representing a potential application."""

    id: str
    url: str
    company: str
    title: str
    status: ApplicationStatus
    discovered_at: datetime
    last_updated_at: datetime
    hash: str
    artifacts: Artifacts = field(default_factory=Artifacts)
    details: JobDetails | None = None
    reason: Reason | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialise the queue item for persistence.

        Returns:
            dict[str, object]: Mapping of queue fields, artifacts, and details.

        """
        payload: dict[str, object] = {
            "id": self.id,
            "url": self.url,
            "company": self.company,
            "title": self.title,
            "status": self.status.value,
            "discovered_at": _dt_to_iso(self.discovered_at),
            "last_updated_at": _dt_to_iso(self.last_updated_at),
            "hash": self.hash,
            "artifacts": self.artifacts.to_dict(),
            "details": self.details.to_dict() if self.details else None,
            "reason": self.reason.to_dict() if self.reason else None,
        }
        return payload

    def to_contract_dict(self) -> dict[str, object]:
        """Return the minimal contract payload exposed to CLI consumers.

        Returns:
            dict[str, object]: Mapping containing id, URL, company, title, and timestamp.

        """
        return {
            "id": self.id,
            "url": self.url,
            "company": self.company,
            "title": self.title,
            "discovered_at": _dt_to_iso(self.discovered_at),
        }

    def update_status(self, new_status: ApplicationStatus, reason: Reason | None = None) -> None:
        """Update status and timestamps with validation."""
        if not _is_valid_transition(self.status, new_status):
            raise ValueError(f"Invalid status transition {self.status.value} -> {new_status.value}")
        self.status = new_status
        self.last_updated_at = _now()
        self.reason = reason

    def attach_artifacts(self, artifacts: Artifacts) -> None:
        """Attach captured artifacts to the item and refresh timestamps.

        Args:
            artifacts: Artifacts captured during processing.

        """
        self.artifacts = artifacts
        self.last_updated_at = _now()

    @classmethod
    def new_from_discovery(
        cls,
        *,
        url: str,
        company: str,
        title: str,
        details: JobDetails | None = None,
        source_query: str | None = None,
        source_rank: int | None = None,
    ) -> ApplicationItem:
        """Create a new queue item with deduplicated hash."""
        discovered_at = _now()
        if details is None:
            details = JobDetails(source_query=source_query, source_rank=source_rank)
        else:
            if source_query is not None:
                details.source_query = source_query
            if source_rank is not None:
                details.source_rank = source_rank
        return cls(
            id=new_ulid(),
            url=url,
            company=company,
            title=title,
            status=ApplicationStatus.NEW,
            discovered_at=discovered_at,
            last_updated_at=discovered_at,
            hash=_fingerprint(url, company, title),
            artifacts=Artifacts(),
            details=details,
        )

    @classmethod
    def from_dict(cls, data: MutableMapping[str, object]) -> ApplicationItem:
        """Construct an :class:`ApplicationItem` from stored mapping data.

        Args:
            data: Mapping representing a persisted application item.

        Returns:
            ApplicationItem: Recreated queue item with nested structures restored.

        """
        details_raw = data.get("details")
        reason_raw = data.get("reason")
        return cls(
            id=str(data["id"]),
            url=str(data["url"]),
            company=str(data["company"]),
            title=str(data["title"]),
            status=ApplicationStatus(str(data.get("status", ApplicationStatus.NEW.value))),
            discovered_at=_maybe_datetime(data.get("discovered_at")) or _now(),
            last_updated_at=_maybe_datetime(data.get("last_updated_at")) or _now(),
            hash=str(data["hash"]),
            artifacts=Artifacts.from_dict(data.get("artifacts", {})),
            details=(
                JobDetails.from_dict(details_raw)
                if isinstance(details_raw, MutableMapping)
                else None
            ),
            reason=Reason(**reason_raw) if isinstance(reason_raw, MutableMapping) else None,
        )


class ApplicationQueue:
    """JSON-backed queue persistence for application items."""

    def __init__(self, profile_id: str, base_dir: Path | None = None) -> None:
        """Initialise a queue for the given profile, loading persisted items.

        Args:
            profile_id: Profile identifier used to namescape queue storage.
            base_dir: Optional directory override for queue persistence.
        """

        self.profile_id = profile_id
        root = Path(base_dir) if base_dir else Path.cwd() / "data" / "queues"
        root.mkdir(parents=True, exist_ok=True)
        self._path = root / f"{profile_id}.json"
        self._items: dict[str, ApplicationItem] = {}
        self._hash_index: dict[str, str] = {}
        if self._path.exists():
            # Tolerate UTF-8 BOM if the file was edited with tools that insert it.
            # Example: PowerShell Out-File -Encoding utf8.
            data = json.loads(self._path.read_text(encoding="utf-8-sig"))
            for raw in data.get("items", []):
                if isinstance(raw, MutableMapping):
                    item = ApplicationItem.from_dict(raw)
                    self._items[item.id] = item
                    self._hash_index[item.hash] = item.id

    def __len__(self) -> int:  # pragma: no cover - trivial
        """Return the number of items stored in the queue."""

        return len(self._items)

    def iter_items(self) -> Iterator[ApplicationItem]:
        """Yield items ordered by discovery timestamp."""

        return iter(sorted(self._items.values(), key=lambda item: item.discovered_at))

    def get(self, item_id: str) -> ApplicationItem | None:
        return self._items.get(item_id)

    def enqueue(self, items: Iterable[ApplicationItem]) -> list[ApplicationItem]:
        accepted: list[ApplicationItem] = []
        for item in items:
            if item.hash in self._hash_index:
                continue
            if item.id in self._items:
                item.id = new_ulid()
            self._items[item.id] = item
            self._hash_index[item.hash] = item.id
            accepted.append(item)
        if accepted:
            log_event(
                "queue.enqueue",
                profile=self.profile_id,
                added=len(accepted),
                total=len(self._items),
            )
            self._persist()
        return accepted

    def pending(self) -> list[ApplicationItem]:
        return [
            item
            for item in self.iter_items()
            if item.status in {ApplicationStatus.NEW, ApplicationStatus.IN_PROGRESS}
        ]

    def update(self, item: ApplicationItem) -> None:
        if item.id not in self._items:
            raise KeyError(f"Unknown application id {item.id}")
        self._items[item.id] = item
        self._hash_index[item.hash] = item.id
        self._persist()

    def mark_submitted(self, item_id: str, confirmation: Artifacts) -> ApplicationItem:
        item = self._require(item_id)
        item.update_status(ApplicationStatus.SUBMITTED)
        item.attach_artifacts(confirmation)
        self.update(item)
        log_event(
            "queue.submitted",
            profile=self.profile_id,
            item=item_id,
            confirmation_id=confirmation.confirmation_id,
        )
        return item

    def mark_failed(
        self,
        item_id: str,
        reason: Reason,
        artifacts: Artifacts | None = None,
    ) -> ApplicationItem:
        item = self._require(item_id)
        item.update_status(ApplicationStatus.FAILED, reason)
        if artifacts:
            item.attach_artifacts(artifacts)
        self.update(item)
        log_event(
            "queue.failed",
            profile=self.profile_id,
            item=item_id,
            reason_code=reason.code,
        )
        return item

    def mark_captcha(
        self,
        item_id: str,
        reason: Reason,
        artifacts: Artifacts | None = None,
    ) -> ApplicationItem:
        item = self._require(item_id)
        item.update_status(ApplicationStatus.CAPTCHA_BLOCKED, reason)
        if artifacts:
            item.attach_artifacts(artifacts)
        self.update(item)
        log_event(
            "queue.captcha",
            profile=self.profile_id,
            item=item_id,
            reason_code=reason.code,
        )
        return item

    def resume(self, item_id: str) -> ApplicationItem:
        item = self._require(item_id)
        item.update_status(ApplicationStatus.IN_PROGRESS)
        self.update(item)
        log_event("queue.resume", profile=self.profile_id, item=item_id)
        return item

    def _require(self, item_id: str) -> ApplicationItem:
        item = self.get(item_id)
        if not item:
            raise LookupError(item_id)
        return item

    def _persist(self) -> None:
        payload = {"items": [item.to_dict() for item in self._items.values()]}
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _fingerprint(url: str, company: str, title: str) -> str:
    digest = hashlib.sha256()
    digest.update(url.encode("utf-8"))
    digest.update(b"|")
    digest.update(company.encode("utf-8"))
    digest.update(b"|")
    digest.update(title.encode("utf-8"))
    return digest.hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _dt_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _maybe_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:  # pragma: no cover - fallback
            return None
    return None


def _maybe_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _maybe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


def _is_valid_transition(old: ApplicationStatus, new: ApplicationStatus) -> bool:
    allowed = {
        ApplicationStatus.NEW: {
            ApplicationStatus.IN_PROGRESS,
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.FAILED,
        },
        ApplicationStatus.IN_PROGRESS: {
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.FAILED,
            ApplicationStatus.CAPTCHA_BLOCKED,
        },
        ApplicationStatus.CAPTCHA_BLOCKED: {
            ApplicationStatus.IN_PROGRESS,
            ApplicationStatus.FAILED,
        },
        ApplicationStatus.SUBMITTED: set(),
        ApplicationStatus.FAILED: set(),
    }
    return new in allowed[old]


def new_ulid() -> str:
    """Generate a ULID-like sortable identifier."""
    ts = int(_now().timestamp() * 1000)
    random_bits = os.urandom(8).hex()
    return f"{ts:012x}{random_bits}"
