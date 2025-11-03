"""Pytest configuration and fixtures for web UI tests."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from web_ui.backend.app import app

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="function")
async def async_client():
    """Async HTTP client for testing FastAPI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def test_profile_id():
    """Test profile ID that exists in profiles/ directory."""
    return "michael_scott_parkin_iii"


@pytest.fixture
def queue_file_path(test_profile_id):
    """Path to test queue file."""
    from web_ui.backend.config import web_settings

    return Path(web_settings.queues_dir) / f"{test_profile_id}.json"
