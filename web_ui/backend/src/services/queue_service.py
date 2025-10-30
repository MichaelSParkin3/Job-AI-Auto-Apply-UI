"""Queue service for managing application queue."""

import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional
from src.models import ApplicationItem, ApplicationStatus
from src.utils import load_json, save_json, FileOpsError

log = logging.getLogger(__name__)


class QueueService:
    """Service for queue management and persistence."""

    def __init__(self, queues_dir: str = "data/queues"):
        """Initialize QueueService.

        Args:
            queues_dir: Directory for queue files
        """
        self.queues_dir = Path(queues_dir)

    def _get_queue_path(self, profile_id: str) -> Path:
        """Get the queue file path for a profile."""
        return self.queues_dir / f"{profile_id}.json"

    def _compute_hash(self, url: str, company: str, title: str) -> str:
        """
        Compute deduplication hash.

        Hash is based on url|company|title to detect duplicate postings.

        Args:
            url: Job URL
            company: Company name
            title: Job title

        Returns:
            SHA256 hash string
        """
        combined = f"{url}|{company}|{title}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def load_queue(self, profile_id: str) -> List[ApplicationItem]:
        """
        Load all items in queue for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            List of ApplicationItem objects

        Raises:
            FileOpsError: If queue not found or invalid JSON
        """
        queue_path = self._get_queue_path(profile_id)

        try:
            if not queue_path.exists():
                return []

            data = load_json(queue_path)
            # Handle both wrapper format {"items": [...]} and raw array [...]
            items_data = data.get("items", []) if isinstance(data, dict) else data
            items = []
            skipped_count = 0

            for idx, item_data in enumerate(items_data):
                try:
                    # Normalize status value if present
                    if "status" in item_data and isinstance(item_data["status"], str):
                        original_status = item_data["status"]
                        item_data["status"] = ApplicationStatus.normalize(original_status)
                        if item_data["status"] != original_status:
                            log.info(
                                f"queue.status_normalized",
                                profile_id=profile_id,
                                item_index=idx,
                                original_status=original_status,
                                normalized_status=item_data["status"],
                            )

                    item = ApplicationItem(**item_data)
                    items.append(item)
                except Exception as e:
                    # Log validation errors instead of silently skipping
                    skipped_count += 1
                    log.warning(
                        f"queue.item_skipped",
                        profile_id=profile_id,
                        item_index=idx,
                        error=str(e),
                        item_summary=f"{item_data.get('company', '?')} - {item_data.get('title', '?')}",
                    )
                    continue

            if skipped_count > 0:
                log.warning(
                    f"queue.load_incomplete",
                    profile_id=profile_id,
                    total_items=len(items_data),
                    loaded_items=len(items),
                    skipped_items=skipped_count,
                )

            return items
        except Exception as e:
            raise FileOpsError(f"Failed to load queue for {profile_id}: {e}")

    def save_queue(self, profile_id: str, items: List[ApplicationItem]) -> None:
        """
        Save queue to file.

        Args:
            profile_id: Profile ID
            items: List of ApplicationItem objects

        Raises:
            FileOpsError: If save fails
        """
        queue_path = self._get_queue_path(profile_id)

        try:
            # Save in wrapper format {"items": [...]} for compatibility with Python CLI
            data = {"items": [item.model_dump() for item in items]}
            save_json(queue_path, data)
        except Exception as e:
            raise FileOpsError(f"Failed to save queue for {profile_id}: {e}")

    def enqueue_job(self, profile_id: str, item: ApplicationItem) -> ApplicationItem:
        """
        Add job to queue with deduplication.

        Items with duplicate hash are skipped.

        Args:
            profile_id: Profile ID
            item: ApplicationItem to add

        Returns:
            The added item

        Raises:
            FileOpsError: If save fails
        """
        items = self.load_queue(profile_id)

        # Compute hash if not set
        if not item.hash:
            item.hash = self._compute_hash(item.url, item.company, item.title)

        # Check for duplicates
        for existing in items:
            if existing.hash == item.hash:
                # Duplicate found, skip
                return existing

        items.append(item)
        self.save_queue(profile_id, items)
        return item

    def get_job(self, profile_id: str, job_id: str) -> Optional[ApplicationItem]:
        """
        Get a specific job from queue.

        Args:
            profile_id: Profile ID
            job_id: Job ID (ULID)

        Returns:
            ApplicationItem or None if not found

        Raises:
            FileOpsError: If queue load fails
        """
        items = self.load_queue(profile_id)
        for item in items:
            if item.id == job_id:
                return item
        return None

    def update_item_status(
        self,
        profile_id: str,
        job_id: str,
        status: ApplicationStatus,
    ) -> ApplicationItem:
        """
        Update job status.

        Args:
            profile_id: Profile ID
            job_id: Job ID
            status: New status

        Returns:
            Updated ApplicationItem

        Raises:
            FileOpsError: If job not found or save fails
        """
        items = self.load_queue(profile_id)

        for i, item in enumerate(items):
            if item.id == job_id:
                item.status = status
                items[i] = item
                self.save_queue(profile_id, items)
                return item

        raise FileOpsError(f"Job not found: {job_id}")

    def remove_item(self, profile_id: str, job_id: str) -> None:
        """
        Remove a job from queue.

        Args:
            profile_id: Profile ID
            job_id: Job ID to remove

        Raises:
            FileOpsError: If job not found or save fails
        """
        items = self.load_queue(profile_id)
        updated = [item for item in items if item.id != job_id]

        if len(updated) == len(items):
            raise FileOpsError(f"Job not found: {job_id}")

        self.save_queue(profile_id, updated)

    def get_status_counts(self, profile_id: str) -> Dict[str, int]:
        """
        Get count of items per status.

        Args:
            profile_id: Profile ID

        Returns:
            Dictionary of status -> count

        Raises:
            FileOpsError: If queue load fails
        """
        items = self.load_queue(profile_id)

        counts = {status.value: 0 for status in ApplicationStatus}

        for item in items:
            counts[item.status.value] += 1

        return counts
