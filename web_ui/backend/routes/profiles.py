"""Routes for profile management."""

import re
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from job_ai_auto_apply_ui.profile_manager import (
    load_profile,
    profiles_root,
    save_profile,
    InvalidProfileError,
)

from ..config import web_settings
from ..models.profile import (
    Profile,
    ProfileListResponse,
    ProfileResponse,
    ProfileDetailResponse,
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ResumeUploadResponse,
)

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
                    Profile(
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

        return ProfileListResponse(profiles=profiles)
    except Exception as e:
        logger.error("Error listing profiles", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    """Get summary for a specific profile."""
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


@router.get("/profiles/{profile_id}/detail", response_model=ProfileDetailResponse)
async def get_profile_detail(profile_id: str):
    """Get complete profile details for editing."""
    try:
        profile = load_profile(profile_id)

        # Build experience items
        experience_list = []
        if profile.experience:
            for exp_item in profile.experience:
                exp_dict = {
                    "company": exp_item.get("company", ""),
                    "role": exp_item.get("role", ""),
                    "dates": exp_item.get("dates", ""),
                    "highlights": exp_item.get("highlights", []),
                    "tech_stack": exp_item.get("tech_stack", []),
                    "metrics": exp_item.get("metrics", {}),
                }
                if "location" in exp_item:
                    exp_dict["location"] = exp_item["location"]
                if "context" in exp_item:
                    exp_dict["context"] = exp_item["context"]
                experience_list.append(exp_dict)

        return ProfileDetailResponse(
            id=profile.id,
            name=profile.name,
            resume_path=str(profile.resume_path) if profile.resume_path else "",
            preferred_browser=profile.preferred_browser,
            user_data_dir=str(profile.user_data_dir) if profile.user_data_dir else None,
            search_query=profile.search_query,
            defaults=dict(profile.defaults) if profile.defaults else {},
            keywords=dict(profile.keywords) if profile.keywords else {},
            experience=experience_list,
            prompts=dict(profile.prompts) if profile.prompts else {},
        )
    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=profile_id)
        raise HTTPException(
            status_code=404, detail=f"Profile '{profile_id}' not found"
        )
    except Exception as e:
        logger.error("Error loading profile detail", profile_id=profile_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


def _validate_profile_id(profile_id: str) -> bool:
    """Validate profile ID format (slug: alphanumeric, underscore, hyphen)."""
    pattern = r"^[a-zA-Z0-9_-]+$"
    return bool(re.match(pattern, profile_id))


@router.post("/profiles", response_model=ProfileDetailResponse, status_code=201)
async def create_profile(req: ProfileCreateRequest):
    """Create a new profile."""
    try:
        # Validate profile ID format
        if not _validate_profile_id(req.id):
            raise ValueError(
                "Profile ID must contain only alphanumeric chars, underscore, and hyphen"
            )

        # Check if profile already exists
        profile_ids = _list_profile_ids()
        if req.id in profile_ids:
            raise ValueError(f"Profile '{req.id}' already exists")

        # Convert request to dict for save_profile
        profile_data = {
            "id": req.id,
            "name": req.name,
            "resume_path": req.resume_path,
            "preferred_browser": req.preferred_browser,
            "user_data_dir": req.user_data_dir,
            "search_query": req.search_query,
            "defaults": req.defaults,
            "keywords": req.keywords,
            "experience": req.experience,
            "prompts": req.prompts,
        }

        # Save profile
        save_profile(req.id, profile_data)
        logger.info("Profile created", profile_id=req.id)

        # Return the created profile
        return req

    except ValueError as e:
        logger.warning("Invalid profile data", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidProfileError as e:
        logger.warning("Profile validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating profile", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profiles/{profile_id}", response_model=ProfileDetailResponse)
async def update_profile(profile_id: str, req: ProfileUpdateRequest):
    """Update an existing profile."""
    try:
        # Load existing profile
        profile = load_profile(profile_id)

        # Build updated data by merging with existing
        profile_data = {
            "id": profile_id,
            "name": req.name or profile.name,
            "resume_path": req.resume_path or str(profile.resume_path),
            "preferred_browser": req.preferred_browser or profile.preferred_browser,
            "user_data_dir": req.user_data_dir or (
                str(profile.user_data_dir) if profile.user_data_dir else None
            ),
            "search_query": req.search_query or profile.search_query,
            "defaults": req.defaults or dict(profile.defaults or {}),
            "keywords": req.keywords or dict(profile.keywords or {}),
            "experience": req.experience or (profile.experience or []),
            "prompts": req.prompts or dict(profile.prompts or {}),
        }

        # Save updated profile
        save_profile(profile_id, profile_data)
        logger.info("Profile updated", profile_id=profile_id)

        # Return updated profile by loading it again
        return await get_profile_detail(profile_id)

    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=profile_id)
        raise HTTPException(
            status_code=404, detail=f"Profile '{profile_id}' not found"
        )
    except InvalidProfileError as e:
        logger.warning("Profile validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error updating profile", profile_id=profile_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(profile_id: str):
    """Delete a profile."""
    try:
        profile_path = profiles_root() / f"{profile_id}.toml"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile '{profile_id}' not found")

        profile_path.unlink()
        logger.info("Profile deleted", profile_id=profile_id)
        return None

    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=profile_id)
        raise HTTPException(
            status_code=404, detail=f"Profile '{profile_id}' not found"
        )
    except Exception as e:
        logger.error("Error deleting profile", profile_id=profile_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profiles/{profile_id}/resume", response_model=ResumeUploadResponse)
async def upload_resume(profile_id: str, file: UploadFile = File(...)):
    """Upload a resume PDF for a profile."""
    try:
        # Validate profile exists
        profile = load_profile(profile_id)

        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are allowed")

        # Validate file size (max 10MB)
        MAX_SIZE = 10 * 1024 * 1024
        file_size = 0

        # Create resumes directory if it doesn't exist
        resumes_dir = Path.cwd() / "resumes"
        resumes_dir.mkdir(parents=True, exist_ok=True)

        # Save file with sanitized name
        # Format: {profile_id}_{original_name}
        safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", file.filename)
        if profile_id not in safe_filename:
            safe_filename = f"{profile_id}_{safe_filename}"

        filepath = resumes_dir / safe_filename

        # Read and save file with size check
        content = await file.read()
        if len(content) > MAX_SIZE:
            raise ValueError(f"File size exceeds maximum allowed (10MB)")

        filepath.write_bytes(content)

        logger.info(
            "Resume uploaded", profile_id=profile_id, filename=safe_filename
        )

        # Return relative path for storage
        relative_path = f"resumes/{safe_filename}"
        return ResumeUploadResponse(
            filename=safe_filename,
            path=relative_path,
        )

    except FileNotFoundError:
        logger.warning("Profile not found", profile_id=profile_id)
        raise HTTPException(
            status_code=404, detail=f"Profile '{profile_id}' not found"
        )
    except ValueError as e:
        logger.warning("Invalid resume upload", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Error uploading resume", profile_id=profile_id, error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
