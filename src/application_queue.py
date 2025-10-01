"""Queue and persistence helpers for application workflow."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError


class ApplicationStatus(str, Enum):
    """Lifecycle states for an application item."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    CAPTCHA_BLOCKED = "captcha_blocked"
    SUBMITTED = "submitted"
    FAILED = "failed"


class WorkModel(str, Enum):
    """Work location models."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class EmploymentType(str, Enum):
    """Employment commitment types."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"
    TEMPORARY = "temporary"
    UNKNOWN = "unknown"


class PayPeriod(str, Enum):
    """Compensation period options."""

    HOURLY = "hourly"
    YEARLY = "yearly"
    UNKNOWN = "unknown"


class Reason(BaseModel):
    """Represents a failure or pause reason."""

    code: str
    message: str


class Compensation(BaseModel):
    """Compensation range for a role."""

    currency: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    period: PayPeriod = PayPeriod.UNKNOWN


class Artifacts(BaseModel):
    """Stored artifact paths for diagnostics."""

    dom_snapshot_path: Optional[str] = None
    screenshot_path: Optional[str] = None
    video_path: Optional[str] = None
    har_path: Optional[str] = None
    confirmation_text: Optional[str] = None
    confirmation_id: Optional[str] = None


class JobDetails(BaseModel):
    """Normalized details about a Lever posting."""

    location: Optional[str] = None
    work_model: WorkModel = WorkModel.UNKNOWN
    employment_type: EmploymentType = EmploymentType.UNKNOWN
    department: Optional[str] = None
    posting_date: Optional[datetime] = None
    compensation: Optional[Compensation] = None
    posting_excerpt: str = ""
    posting_text: str = ""
    tech_tags: List[str] = Field(default_factory=list)
    source_query: Optional[str] = None
    source_rank: Optional[int] = None
    apply_url: Optional[str] = None
    closed: bool = False
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApplicationItem(BaseModel):
    """Item in the application queue."""

    id: str
    url: str
    company: str
    title: str
    status: ApplicationStatus = ApplicationStatus.NEW
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reason: Optional[Reason] = None
    artifacts: Artifacts = Field(default_factory=Artifacts)
    hash: str
    details: JobDetails = Field(default_factory=JobDetails)

    def transition(self, status: ApplicationStatus, reason: Optional[Reason] = None) -> None:
        """Update status and timestamps with validation."""
        allowed = {
            ApplicationStatus.NEW: {ApplicationStatus.IN_PROGRESS},
            ApplicationStatus.IN_PROGRESS: {
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.FAILED,
                ApplicationStatus.CAPTCHA_BLOCKED,
            },
            ApplicationStatus.CAPTCHA_BLOCKED: {ApplicationStatus.IN_PROGRESS},
        }
        if status == self.status:
            return
        if self.status in allowed and status not in allowed[self.status]:
            raise ValueError(f"Invalid status transition from {self.status} to {status}")
        self.status = status
        self.reason = reason
        self.last_updated_at = datetime.now(UTC)

    def update_details(self, details: JobDetails) -> None:
        """Replace job details and update timestamp."""
        self.details = details
        self.last_updated_at = datetime.now(UTC)


@dataclass
class EnqueueResult:
    """Result from enqueue attempt."""

    item: ApplicationItem
    created: bool


class ApplicationQueue:
    """Manage persistence of application items for a profile."""

    def __init__(self, profile_id: str, storage_dir: Path | None = None) -> None:
        self.profile_id = profile_id
        env_base = os.environ.get("JOB_APPLY_DATA_DIR")
        if storage_dir is None:
            storage_dir = Path(env_base) / "queues" if env_base else Path("data/queues")
        self.storage_dir = Path(storage_dir)
        self.storage_path = self.storage_dir / f"{profile_id}.json"
        self._items: Dict[str, ApplicationItem] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
        items = {}
        for payload in raw:
            try:
                item = ApplicationItem.model_validate(payload)
            except ValidationError as exc:  # pragma: no cover - indicates corrupted state
                raise RuntimeError(f"Invalid queue payload for {self.profile_id}") from exc
            items[item.id] = item
        self._items = items

    def _dump(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump(mode="json") for item in self._items.values()]
        self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._items)

    def list_items(self) -> List[ApplicationItem]:
        return list(self._items.values())

    def get(self, item_id: str) -> Optional[ApplicationItem]:
        return self._items.get(item_id)

    def enqueue(
        self,
        *,
        url: str,
        company: str,
        title: str,
        details: Optional[JobDetails] = None,
    ) -> EnqueueResult:
        fingerprint = _compute_hash(url=url, company=company, title=title)
        for existing in self._items.values():
            if existing.hash == fingerprint:
                return EnqueueResult(existing, False)
        item = ApplicationItem(
            id=_generate_ulid(),
            url=url,
            company=company,
            title=title,
            hash=fingerprint,
            details=details or JobDetails(),
        )
        self._items[item.id] = item
        self._dump()
        return EnqueueResult(item, True)

    def update_item(
        self,
        item_id: str,
        *,
        status: Optional[ApplicationStatus] = None,
        reason: Optional[Reason] = None,
        details: Optional[JobDetails] = None,
        artifacts: Optional[Artifacts] = None,
    ) -> ApplicationItem:
        item = self._items.get(item_id)
        if item is None:
            raise KeyError(f"Item {item_id} not found in queue")
        if status is not None:
            item.transition(status, reason)
        elif reason is not None:
            item.reason = reason
        if details is not None:
            item.update_details(details)
        if artifacts is not None:
            item.artifacts = artifacts
        item.last_updated_at = datetime.now(UTC)
        self._dump()
        return item

    def remove(self, item_id: str) -> None:
        if item_id in self._items:
            del self._items[item_id]
            self._dump()


def _compute_hash(*, url: str, company: str, title: str) -> str:
    payload = f"{url}|{company}|{title}".encode("utf-8")
    return sha256(payload).hexdigest()


_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _generate_ulid() -> str:
    """Generate a ULID string without external dependencies."""
    timestamp = int(datetime.now(UTC).timestamp() * 1000)
    time_bytes = timestamp.to_bytes(6, "big")
    randomness = os.urandom(10)
    data = time_bytes + randomness
    value = int.from_bytes(data, "big")
    encoded = []
    for _ in range(26):
        value, idx = divmod(value, 32)
        encoded.append(_ULID_ALPHABET[idx])
    return "".join(reversed(encoded))
