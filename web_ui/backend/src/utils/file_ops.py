"""File operations utility with atomic writes and BOM handling."""

import os
import json
import toml
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Union, Optional


class FileOpsError(Exception):
    """Base exception for file operations."""

    pass


class AtomicFileError(FileOpsError):
    """Exception for atomic write failures."""

    pass


def ensure_dir(path: Union[str, Path]) -> None:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path to create

    Raises:
        FileOpsError: If unable to create directory
    """
    try:
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise FileOpsError(f"Failed to create directory {path}: {e}")


def load_toml(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load TOML file.

    Args:
        path: Path to TOML file

    Returns:
        Parsed TOML data as dictionary

    Raises:
        FileOpsError: If file not found or invalid TOML
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileOpsError(f"TOML file not found: {path}")
        with open(path_obj, "r", encoding="utf-8") as f:
            return toml.load(f)
    except FileOpsError:
        raise
    except Exception as e:
        raise FileOpsError(f"Failed to load TOML {path}: {e}")


def save_toml(path: Union[str, Path], data: Dict[str, Any]) -> None:
    """
    Save TOML file with atomic write.

    Atomic write pattern:
    1. Write to temporary file in same directory
    2. Verify write success (fsync)
    3. Atomic rename (os.replace)
    4. On failure, original file remains unchanged

    Args:
        path: Path to TOML file
        data: Data to save

    Raises:
        AtomicFileError: If atomic write fails
    """
    path_obj = Path(path)
    ensure_dir(path_obj.parent)

    try:
        # Create temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path_obj.parent,
            prefix=".tmp_",
            suffix=".toml",
        )

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                toml.dump(data, f)
                f.flush()
                os.fsync(f.fileno())  # Ensure write to disk

            # Atomic rename
            os.replace(temp_path, path_obj)
        except Exception as e:
            # Cleanup temp file on failure
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise AtomicFileError(f"Failed to save TOML {path}: {e}")
    except AtomicFileError:
        raise
    except Exception as e:
        raise AtomicFileError(f"Atomic write failed for {path}: {e}")


def load_json(
    path: Union[str, Path],
    utf8_sig: bool = True,
) -> Union[Dict[str, Any], List[Any]]:
    """
    Load JSON file with UTF-8 BOM handling.

    Args:
        path: Path to JSON file
        utf8_sig: Handle UTF-8 BOM (default True for queue files)

    Returns:
        Parsed JSON data

    Raises:
        FileOpsError: If file not found or invalid JSON
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileOpsError(f"JSON file not found: {path}")

        encoding = "utf-8-sig" if utf8_sig else "utf-8"
        with open(path_obj, "r", encoding=encoding) as f:
            return json.load(f)
    except FileOpsError:
        raise
    except json.JSONDecodeError as e:
        raise FileOpsError(f"Invalid JSON in {path}: {e}")
    except Exception as e:
        raise FileOpsError(f"Failed to load JSON {path}: {e}")


def save_json(path: Union[str, Path], data: Union[Dict[str, Any], List[Any]]) -> None:
    """
    Save JSON file with atomic write.

    Args:
        path: Path to JSON file
        data: Data to save

    Raises:
        AtomicFileError: If atomic write fails
    """
    path_obj = Path(path)
    ensure_dir(path_obj.parent)

    try:
        # Create temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path_obj.parent,
            prefix=".tmp_",
            suffix=".json",
        )

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())  # Ensure write to disk

            # Atomic rename
            os.replace(temp_path, path_obj)
        except Exception as e:
            # Cleanup temp file on failure
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise AtomicFileError(f"Failed to save JSON {path}: {e}")
    except AtomicFileError:
        raise
    except Exception as e:
        raise AtomicFileError(f"Atomic write failed for {path}: {e}")


def load_env(path: Union[str, Path]) -> Dict[str, str]:
    """
    Load environment variables from .env file.

    Args:
        path: Path to .env file

    Returns:
        Dictionary of environment variables

    Raises:
        FileOpsError: If file not found
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return {}

        env_vars = {}
        with open(path_obj, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

        return env_vars
    except Exception as e:
        raise FileOpsError(f"Failed to load .env from {path}: {e}")


def save_env(path: Union[str, Path], updates: Dict[str, str]) -> None:
    """
    Save environment variables to .env file, preserving existing values and comments.

    Args:
        path: Path to .env file
        updates: Dictionary of environment variables to update/add

    Raises:
        AtomicFileError: If atomic write fails
    """
    path_obj = Path(path)
    ensure_dir(path_obj.parent)

    try:
        # Load existing content
        existing_lines = []
        if path_obj.exists():
            with open(path_obj, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()

        # Build new content preserving structure
        new_lines = []
        updated_keys = set()

        for line in existing_lines:
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0].strip()
                if key in updates:
                    # Update existing key
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    # Keep existing line
                    new_lines.append(line)
            else:
                # Keep comments and empty lines
                new_lines.append(line)

        # Add new keys
        for key, value in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}\n")

        # Atomic write
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path_obj.parent,
            prefix=".tmp_",
            suffix=".env",
        )

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, path_obj)
        except Exception as e:
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise AtomicFileError(f"Failed to save .env {path}: {e}")
    except AtomicFileError:
        raise
    except Exception as e:
        raise AtomicFileError(f"Atomic write failed for {path}: {e}")
