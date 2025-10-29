"""Artifact service for managing application artifacts."""

import mimetypes
from pathlib import Path
from typing import List, Dict, Optional
from src.utils import FileOpsError


class ArtifactService:
    """Service for artifact file management and serving."""

    def __init__(self, artifacts_dir: str = "data/artifacts"):
        """Initialize ArtifactService.

        Args:
            artifacts_dir: Base directory for artifacts
        """
        self.artifacts_dir = Path(artifacts_dir)

    def _get_artifact_dir(self, profile_id: str, job_id: str) -> Path:
        """Get artifact directory for a job."""
        return self.artifacts_dir / profile_id / job_id

    def list_artifacts(self, profile_id: str, job_id: str) -> List[Dict]:
        """List artifacts for a job."""
        artifact_dir = self._get_artifact_dir(profile_id, job_id)

        if not artifact_dir.exists():
            return []

        artifacts = []
        for file_path in artifact_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                mime_type, _ = mimetypes.guess_type(str(file_path))

                artifacts.append({
                    "name": file_path.name,
                    "type": mime_type or "application/octet-stream",
                    "size_bytes": stat.st_size,
                    "created_at": stat.st_mtime,
                })

        return artifacts

    def get_artifact_file(self, profile_id: str, job_id: str, filename: str) -> bytes:
        """Get artifact file content."""
        # Prevent directory traversal
        if ".." in filename or filename.startswith("/"):
            raise FileOpsError("Invalid filename")

        file_path = self._get_artifact_dir(profile_id, job_id) / filename

        # Verify file is within artifact directory
        if not file_path.resolve().is_relative_to(self.artifacts_dir.resolve()):
            raise FileOpsError("Access denied")

        if not file_path.exists():
            raise FileOpsError("Artifact not found")

        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise FileOpsError(f"Failed to read artifact: {e}")

    def get_artifact_metadata(self, profile_id: str, job_id: str) -> Dict:
        """Get metadata for all artifacts of a job."""
        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "artifacts": self.list_artifacts(profile_id, job_id),
        }
