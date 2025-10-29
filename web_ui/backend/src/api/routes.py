"""API routes with dependency injection."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from src.app import app_context, app
from src.models import Profile, ApplicationItem, Setting, RunConfiguration
from src.services import (
    ProfileService,
    QueueService,
    SettingsService,
    ArtifactService,
    CLIService,
)


# Dependency injection functions
def get_profile_service() -> ProfileService:
    """Get ProfileService instance."""
    return app_context.profile_service


def get_queue_service() -> QueueService:
    """Get QueueService instance."""
    return app_context.queue_service


def get_settings_service() -> SettingsService:
    """Get SettingsService instance."""
    return app_context.settings_service


def get_artifact_service() -> ArtifactService:
    """Get ArtifactService instance."""
    return app_context.artifact_service


def get_cli_service() -> CLIService:
    """Get CLIService instance."""
    return app_context.cli_service


# Create API router
router = APIRouter(prefix="/api/v1")


# ============================================================================
# PROFILES ENDPOINTS
# ============================================================================

@router.get("/profiles", tags=["profiles"])
async def list_profiles(
    profile_service: ProfileService = Depends(get_profile_service),
) -> Dict[str, Any]:
    """List all profiles."""
    try:
        profiles = profile_service.list_profiles()
        return {
            "profiles": [p.model_dump() for p in profiles],
            "count": len(profiles),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}", tags=["profiles"])
async def get_profile(
    profile_id: str,
    profile_service: ProfileService = Depends(get_profile_service),
) -> Dict[str, Any]:
    """Get specific profile."""
    try:
        profile = profile_service.get_profile(profile_id)
        return profile.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/profiles/{profile_id}", tags=["profiles"])
async def update_profile(
    profile_id: str,
    profile_data: Profile,
    profile_service: ProfileService = Depends(get_profile_service),
) -> Dict[str, Any]:
    """Update profile."""
    try:
        updated = profile_service.update_profile(profile_id, profile_data)
        return updated.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/profiles/{profile_id}/switch", tags=["profiles"])
async def switch_profile(
    profile_id: str,
    profile_service: ProfileService = Depends(get_profile_service),
) -> Dict[str, str]:
    """Switch active profile."""
    try:
        profile_service.set_active_profile(profile_id)
        return {"profile_id": profile_id, "status": "switched"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profiles/{profile_id}/queue", tags=["profiles"])
async def get_profile_queue(
    profile_id: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> Dict[str, Any]:
    """Get queue for profile."""
    try:
        items = queue_service.load_queue(profile_id)
        counts = queue_service.get_status_counts(profile_id)
        return {
            "profile_id": profile_id,
            "items": [i.model_dump() for i in items],
            "count": len(items),
            "status_counts": counts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# JOBS ENDPOINTS
# ============================================================================

@router.get("/jobs", tags=["jobs"])
async def list_jobs(
    profile_id: str,
    status: Optional[str] = None,
    queue_service: QueueService = Depends(get_queue_service),
) -> Dict[str, Any]:
    """List jobs for profile."""
    try:
        items = queue_service.load_queue(profile_id)
        if status:
            items = [i for i in items if i.status.value == status]
        return {
            "profile_id": profile_id,
            "items": [i.model_dump() for i in items],
            "count": len(items),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", tags=["jobs"])
async def get_job(
    job_id: str,
    profile_id: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> Dict[str, Any]:
    """Get specific job details."""
    try:
        item = queue_service.get_job(profile_id, job_id)
        if not item:
            raise HTTPException(status_code=404, detail="Job not found")
        return item.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/jobs/{job_id}/status", tags=["jobs"])
async def update_job_status(
    job_id: str,
    profile_id: str,
    status: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> Dict[str, Any]:
    """Update job status."""
    try:
        from src.models import ApplicationStatus
        item = queue_service.update_item_status(
            profile_id, job_id, ApplicationStatus(status)
        )
        return item.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/jobs/{job_id}", tags=["jobs"])
async def delete_job(
    job_id: str,
    profile_id: str,
    queue_service: QueueService = Depends(get_queue_service),
) -> Dict[str, str]:
    """Delete job from queue."""
    try:
        queue_service.remove_item(profile_id, job_id)
        return {"status": "deleted", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# DISCOVERY ENDPOINTS
# ============================================================================

@router.post("/discover/execute", tags=["discovery"])
async def execute_discovery(
    profile_id: str,
    search_window: Optional[str] = None,
    job_cap: Optional[int] = None,
) -> Dict[str, str]:
    """Execute discovery (stub)."""
    return {
        "status": "started",
        "profile_id": profile_id,
        "message": "Discovery execution initiated",
    }


@router.get("/discover/status", tags=["discovery"])
async def get_discovery_status(
    profile_id: str,
) -> Dict[str, Any]:
    """Get discovery status (stub)."""
    return {
        "profile_id": profile_id,
        "status": "idle",
        "progress": 0,
    }


@router.get("/discover/last-options/{profile_id}", tags=["discovery"])
async def get_last_discovery_options(
    profile_id: str,
    settings_service: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Get last discovery options (stub)."""
    return {
        "profile_id": profile_id,
        "search_window": "24h",
        "job_cap": 10,
    }


# ============================================================================
# APPLY ENDPOINTS
# ============================================================================

@router.post("/apply/single", tags=["apply"])
async def apply_single(
    profile_id: str,
    job_id: str,
) -> Dict[str, str]:
    """Apply to single job (stub)."""
    return {
        "status": "started",
        "profile_id": profile_id,
        "job_id": job_id,
    }


@router.post("/apply/bulk", tags=["apply"])
async def apply_bulk(
    profile_id: str,
) -> Dict[str, str]:
    """Apply to multiple jobs (stub)."""
    return {
        "status": "started",
        "profile_id": profile_id,
    }


@router.get("/apply/status/{job_id}", tags=["apply"])
async def get_apply_status(
    job_id: str,
    profile_id: str,
) -> Dict[str, Any]:
    """Get apply status (stub)."""
    return {
        "job_id": job_id,
        "status": "pending",
    }


@router.get("/apply/logs/{job_id}", tags=["apply"])
async def get_apply_logs(
    job_id: str,
    profile_id: str,
) -> Dict[str, Any]:
    """Get apply logs (stub)."""
    return {
        "job_id": job_id,
        "logs": [],
    }


# ============================================================================
# ARTIFACTS ENDPOINTS
# ============================================================================

@router.get("/artifacts/{profile_id}/{job_id}/", tags=["artifacts"])
async def list_artifacts(
    profile_id: str,
    job_id: str,
    artifact_service: ArtifactService = Depends(get_artifact_service),
) -> Dict[str, Any]:
    """List artifacts for job."""
    try:
        artifacts = artifact_service.list_artifacts(profile_id, job_id)
        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "artifacts": artifacts,
            "count": len(artifacts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/{profile_id}/{job_id}/{filename}", tags=["artifacts"])
async def get_artifact(
    profile_id: str,
    job_id: str,
    filename: str,
    artifact_service: ArtifactService = Depends(get_artifact_service),
) -> Dict[str, Any]:
    """Get artifact file (stub)."""
    try:
        data = artifact_service.get_artifact_file(profile_id, job_id, filename)
        return {
            "profile_id": profile_id,
            "job_id": job_id,
            "filename": filename,
            "size": len(data),
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@router.get("/settings", tags=["settings"])
async def list_settings(
    settings_service: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """List all settings."""
    try:
        settings = settings_service.get_all_settings()
        return {
            "settings": [s.model_dump() for s in settings],
            "count": len(settings),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings/{key}", tags=["settings"])
async def get_setting(
    key: str,
    settings_service: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Get specific setting."""
    try:
        setting = settings_service.get_setting(key)
        return setting.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/settings", tags=["settings"])
async def update_settings(
    updates: Dict[str, str],
    settings_service: SettingsService = Depends(get_settings_service),
) -> Dict[str, Any]:
    """Update settings."""
    try:
        keys = settings_service.update_settings(updates)
        return {"updated": keys, "count": len(keys)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/settings/{key}", tags=["settings"])
async def reset_setting(
    key: str,
    settings_service: SettingsService = Depends(get_settings_service),
) -> Dict[str, str]:
    """Reset setting to default."""
    try:
        settings_service.reset_setting(key)
        return {"status": "reset", "key": key}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/settings/reset", tags=["settings"])
async def reset_all_settings(
    settings_service: SettingsService = Depends(get_settings_service),
) -> Dict[str, str]:
    """Reset all settings."""
    try:
        settings_service.reset_all()
        return {"status": "all_settings_reset"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Include router in app
app.include_router(router)
