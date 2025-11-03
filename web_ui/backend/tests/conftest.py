"""Pytest configuration for web UI backend tests."""

import sys
import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app_with_context():
    """Initialize app with proper context for testing."""
    from src.app import app, app_context
    from src.services import (
        ProfileService,
        QueueService,
        SettingsService,
        ArtifactService,
        CLIService,
        RunConfigurationService,
    )
    import os

    # Initialize app context manually for tests
    app_context.profile_service = ProfileService(os.getenv("PROFILES_DIR", "../../profiles"))
    app_context.queue_service = QueueService(os.getenv("QUEUES_DIR", "../../data/queues"))
    app_context.settings_service = SettingsService(os.getenv("SETTINGS_FILE", "../../.env"))
    app_context.artifact_service = ArtifactService(os.getenv("ARTIFACTS_DIR", "../../data/artifacts"))
    app_context.cli_service = CLIService(os.getenv("CLI_COMMAND", "auto-apply"))
    app_context.run_config_service = RunConfigurationService(os.getenv("RUN_CONFIG_DIR", "../../data/run-config"))

    return app


@pytest.fixture
def client(app_with_context):
    """Create a TestClient with initialized app context."""
    return TestClient(app_with_context)
