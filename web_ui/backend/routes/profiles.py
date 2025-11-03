"""Routes for profile management."""

from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException

from job_ai_auto_apply_ui.profile_manager import load_profile, profiles_root

from ..config import web_settings
from ..models.profile import ProfileListResponse, ProfileResponse

router = APIRouter()
logger = structlog.get_logger()


def _list_profile_ids() -> list[str]:
    """List all profile IDs from profiles directory."""
    profiles_path = profiles_root()
    if not profiles_path.exists():
        return []

    # Find all .toml files in profiles directory
    profile_ids = []
    for toml_file in profiles_path.glob("*.toml"):
        profile_id = toml_file.stem
        profile_ids.append(profile_id)

    return sorted(profile_ids)


@router.get("/profiles", response_model=ProfileListResponse)
async def get_profiles():
    """List all available profiles from profiles/ directory."""
    try:
        profile_ids = _list_profile_ids()
        profiles = []

        for profile_id in profile_ids:
            try:
                profile = load_profile(profile_id)
                profiles.append(
                    ProfileResponse(
                        id=profile.id,
                        name=profile.name,
                        resume_path=str(profile.resume_path) if profile.resume_path else "",
                        preferred_browser=profile.preferred_browser,
                        has_experience=len(profile.experience or []) > 0,
                    )
                )
            except Exception as e:
                logger.warning(
                    "Failed to load profile",
                    profile_id=profile_id,
                    error=str(e),
                )

        return ProfileListResponse(profiles=profiles, count=len(profiles))
    except Exception as e:
        logger.error("Error listing profiles", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    """Get details for a specific profile."""
    try:
        profile = load_profile(profile_id)
        return ProfileResponse(
            id=profile.id,
            name=profile.name,
            resume_path=str(profile.resume_path) if profile.resume_path else "",
            preferred_browser=profile.preferred_browser,
            has_experience=len(profile.experience or []) > 0,
        )
    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=profile_id)
        raise HTTPException(
            status_code=404, detail=f"Profile '{profile_id}' not found"
        )
    except Exception as e:
        logger.error("Error loading profile", profile_id=profile_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
