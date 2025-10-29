"""Unit tests for ArtifactService."""

import tempfile
from pathlib import Path

import pytest

from src.services import ArtifactService
from src.utils import FileOpsError


class TestArtifactService:
    """Test cases for ArtifactService."""

    @pytest.fixture
    def temp_artifacts_dir(self) -> Path:
        """Create temporary artifacts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def service(self, temp_artifacts_dir: Path) -> ArtifactService:
        """Create ArtifactService instance with temp dir."""
        return ArtifactService(str(temp_artifacts_dir))

    def test_list_artifacts_empty_directory(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test listing artifacts when directory doesn't exist."""
        artifacts = service.list_artifacts("profile1", "job1")
        assert artifacts == []

    def test_list_artifacts_with_files(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test listing artifacts when files exist."""
        # Create artifact directory and files
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        # Create test files
        (artifact_dir / "screenshot.png").write_bytes(b"PNG_CONTENT")
        (artifact_dir / "video.mp4").write_bytes(b"VIDEO_CONTENT")

        artifacts = service.list_artifacts("profile1", "job1")

        assert len(artifacts) == 2
        assert any(a["name"] == "screenshot.png" for a in artifacts)
        assert any(a["name"] == "video.mp4" for a in artifacts)

    def test_list_artifacts_ignores_subdirectories(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test that subdirectories are ignored."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        # Create file and subdirectory
        (artifact_dir / "screenshot.png").write_bytes(b"PNG")
        (artifact_dir / "subdir").mkdir()

        artifacts = service.list_artifacts("profile1", "job1")

        # Should only return file, not directory
        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "screenshot.png"

    def test_get_artifact_file_success(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test successfully getting artifact file content."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        test_content = b"TEST_FILE_CONTENT"
        (artifact_dir / "test.txt").write_bytes(test_content)

        content = service.get_artifact_file("profile1", "job1", "test.txt")

        assert content == test_content

    def test_get_artifact_file_not_found(
        self, service: ArtifactService
    ) -> None:
        """Test getting artifact that doesn't exist."""
        with pytest.raises(FileOpsError, match="Artifact not found"):
            service.get_artifact_file("profile1", "job1", "nonexistent.txt")

    def test_get_artifact_file_directory_traversal_protection_parent_dirs(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test protection against directory traversal with ..."""
        # Attempt to access parent directory
        with pytest.raises(FileOpsError, match="Invalid filename"):
            service.get_artifact_file("profile1", "job1", "../../../etc/passwd")

    def test_get_artifact_file_directory_traversal_protection_absolute_path(
        self, service: ArtifactService
    ) -> None:
        """Test protection against absolute paths."""
        with pytest.raises(FileOpsError, match="Invalid filename"):
            service.get_artifact_file("profile1", "job1", "/etc/passwd")

    def test_get_artifact_file_relative_path_check(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test that file must be within artifact directory."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        # Create file outside artifact dir
        outside_file = temp_artifacts_dir / "outside.txt"
        outside_file.write_bytes(b"OUTSIDE")

        # Attempt to access it (should fail even with proper path manipulation)
        with pytest.raises(FileOpsError, match="Access denied"):
            service.get_artifact_file(
                "profile1", "job1", str(outside_file.relative_to(artifact_dir))
            )

    def test_get_artifact_metadata(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test getting metadata for artifacts."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        (artifact_dir / "file1.txt").write_bytes(b"content")
        (artifact_dir / "file2.txt").write_bytes(b"more")

        metadata = service.get_artifact_metadata("profile1", "job1")

        assert metadata["profile_id"] == "profile1"
        assert metadata["job_id"] == "job1"
        assert len(metadata["artifacts"]) == 2

    def test_artifact_mimetype_detection(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test that MIME types are correctly detected."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        (artifact_dir / "image.png").write_bytes(b"PNG")
        (artifact_dir / "video.mp4").write_bytes(b"VIDEO")
        (artifact_dir / "document.pdf").write_bytes(b"PDF")

        artifacts = service.list_artifacts("profile1", "job1")

        # Check MIME types
        mime_types = {a["name"]: a["type"] for a in artifacts}
        assert mime_types["image.png"] == "image/png"
        assert mime_types["video.mp4"] == "video/mp4"
        assert mime_types["document.pdf"] == "application/pdf"

    def test_artifact_file_size(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test that file sizes are correctly reported."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        content = b"A" * 1024  # 1KB
        (artifact_dir / "file.bin").write_bytes(content)

        artifacts = service.list_artifacts("profile1", "job1")

        assert len(artifacts) == 1
        assert artifacts[0]["size_bytes"] == 1024

    def test_multiple_profiles_isolation(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test that artifacts are isolated per profile."""
        # Create artifacts for different profiles
        dir1 = temp_artifacts_dir / "profile1" / "job1"
        dir1.mkdir(parents=True)
        (dir1 / "file1.txt").write_bytes(b"profile1_content")

        dir2 = temp_artifacts_dir / "profile2" / "job1"
        dir2.mkdir(parents=True)
        (dir2 / "file2.txt").write_bytes(b"profile2_content")

        artifacts1 = service.list_artifacts("profile1", "job1")
        artifacts2 = service.list_artifacts("profile2", "job1")

        assert len(artifacts1) == 1
        assert len(artifacts2) == 1
        assert artifacts1[0]["name"] == "file1.txt"
        assert artifacts2[0]["name"] == "file2.txt"

    def test_multiple_jobs_isolation(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test that artifacts are isolated per job."""
        # Create artifacts for different jobs
        dir1 = temp_artifacts_dir / "profile1" / "job1"
        dir1.mkdir(parents=True)
        (dir1 / "job1_file.txt").write_bytes(b"job1")

        dir2 = temp_artifacts_dir / "profile1" / "job2"
        dir2.mkdir(parents=True)
        (dir2 / "job2_file.txt").write_bytes(b"job2")

        artifacts1 = service.list_artifacts("profile1", "job1")
        artifacts2 = service.list_artifacts("profile1", "job2")

        assert len(artifacts1) == 1
        assert len(artifacts2) == 1
        assert artifacts1[0]["name"] == "job1_file.txt"
        assert artifacts2[0]["name"] == "job2_file.txt"

    def test_get_artifact_file_binary_data(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test reading binary artifact files."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        # Create binary file with non-ASCII bytes
        binary_data = bytes(range(256))
        (artifact_dir / "binary.dat").write_bytes(binary_data)

        content = service.get_artifact_file("profile1", "job1", "binary.dat")

        assert content == binary_data

    def test_artifact_creation_timestamp(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test that artifact creation timestamp is captured."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        (artifact_dir / "file.txt").write_bytes(b"content")

        artifacts = service.list_artifacts("profile1", "job1")

        assert len(artifacts) == 1
        assert "created_at" in artifacts[0]
        assert isinstance(artifacts[0]["created_at"], float)
        assert artifacts[0]["created_at"] > 0

    def test_get_artifact_file_handles_special_characters(
        self, service: ArtifactService, temp_artifacts_dir: Path
    ) -> None:
        """Test handling of files with special characters in names."""
        artifact_dir = temp_artifacts_dir / "profile1" / "job1"
        artifact_dir.mkdir(parents=True)

        # Create file with special characters
        filename = "screenshot_2025-10-28_10-30-45.png"
        (artifact_dir / filename).write_bytes(b"PNG")

        content = service.get_artifact_file("profile1", "job1", filename)

        assert content == b"PNG"
