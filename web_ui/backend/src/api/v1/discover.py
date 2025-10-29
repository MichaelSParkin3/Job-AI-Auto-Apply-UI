"""Discovery API endpoints for job discovery workflow."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from src.models.config import RunConfiguration, OperationType
from src.models.application import ApplicationStatus
from src.services.cli_service import CLIService
from src.services.queue_service import QueueService
from src.services.run_config_service import RunConfigurationService

router = APIRouter(prefix="/discover", tags=["discover"])

# Service instances (would normally be injected)
cli_service = CLIService()
queue_service = QueueService()
run_config_service = RunConfigurationService()


class DiscoveryRequest(BaseModel):
    """Request model for starting a discovery operation."""

    profile_id: str = Field(..., description="Profile ID to discover jobs for")
    search_window: str = Field(default="24h", description="Search window (e.g., 24h, 7d)")
    job_cap: int = Field(default=10, description="Maximum jobs to discover", ge=1, le=1000)
    custom_query: Optional[str] = Field(None, description="Custom search query")


class DiscoveryProgress(BaseModel):
    """Progress update for ongoing discovery."""

    status: str = Field(..., description="Current status message")
    discovered_count: int = Field(..., description="Number of jobs discovered so far")
    progress_percent: int = Field(..., description="Estimated progress percentage", ge=0, le=100)


class DiscoveryResult(BaseModel):
    """Result of a discovery operation."""

    total_discovered: int = Field(..., description="Total jobs discovered")
    total_enqueued: int = Field(..., description="Jobs added to queue")
    status: str = Field(..., description="Final status message")


class LastOptions(BaseModel):
    """Last-used discovery options for a profile."""

    profile_id: str
    operation_type: str = Field(default="discover")
    search_window: Optional[str] = None
    job_cap: Optional[int] = None
    custom_query: Optional[str] = None


@router.post("/execute", response_model=DiscoveryResult)
async def execute_discovery(request: DiscoveryRequest) -> DiscoveryResult:
    """Start a job discovery operation.

    Args:
        request: Discovery request with profile and options

    Returns:
        DiscoveryResult with total discovered and enqueued counts

    Raises:
        HTTPException: If discovery fails or profile not found
    """
    try:
        # Save the options for next time
        config = RunConfiguration(
            profile_id=request.profile_id,
            operation_type=OperationType.DISCOVER,
            search_window=request.search_window,
            job_cap=request.job_cap,
            custom_query=request.custom_query,
        )
        run_config_service.save_run_config(request.profile_id, config)

        # Execute discovery via CLI
        discovered_count = 0
        enqueued_count = 0

        # Stream events from CLI discovery
        async for event in cli_service.execute_discover(
            profile_id=request.profile_id,
            search_window=request.search_window,
            job_cap=request.job_cap,
            custom_query=request.custom_query,
        ):
            # Parse event and update counts
            if event.get("type") == "item.discovered":
                discovered_count += 1
            elif event.get("type") == "item.enqueued":
                enqueued_count += 1

        return DiscoveryResult(
            total_discovered=discovered_count,
            total_enqueued=enqueued_count,
            status="success" if discovered_count > 0 else "no results",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")


@router.get("/status")
async def get_discovery_status() -> dict:
    """Get current discovery progress status.

    Note: This is a simplified implementation. In production,
    you would track discovery state in a background task.

    Returns:
        Current status with progress information
    """
    return {
        "status": "not_running",
        "message": "No discovery in progress",
        "discovered_count": 0,
        "progress_percent": 0,
    }


@router.get("/last-options/{profile_id}", response_model=LastOptions)
async def get_last_discovery_options(profile_id: str) -> LastOptions:
    """Get last-used discovery options for a profile.

    Args:
        profile_id: Profile ID

    Returns:
        LastOptions with saved search parameters

    Raises:
        HTTPException: If profile not found
    """
    try:
        config = run_config_service.load_run_config(
            profile_id, OperationType.DISCOVER
        )
        return LastOptions(
            profile_id=profile_id,
            operation_type="discover",
            search_window=config.search_window,
            job_cap=config.job_cap,
            custom_query=config.custom_query,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load options: {str(e)}")
