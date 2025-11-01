"""FastAPI application initialization and configuration."""

import os
import json
import logging
from typing import Dict, Any
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()


# Initialize services at app startup
class AppContext:
    """Application context for dependency injection."""

    def __init__(self):
        self.profile_service = None
        self.queue_service = None
        self.settings_service = None
        self.artifact_service = None
        self.cli_service = None


app_context = AppContext()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context."""
    # Startup
    from src.services import (
        ProfileService,
        QueueService,
        SettingsService,
        ArtifactService,
        CLIService,
    )

    app_context.profile_service = ProfileService(os.getenv("PROFILES_DIR", "../../profiles"))
    app_context.queue_service = QueueService(os.getenv("QUEUES_DIR", "../../data/queues"))
    app_context.settings_service = SettingsService(os.getenv("SETTINGS_FILE", "../../.env"))
    app_context.artifact_service = ArtifactService(os.getenv("ARTIFACTS_DIR", "../../data/artifacts"))
    app_context.cli_service = CLIService(os.getenv("CLI_COMMAND", "auto-apply"))

    log.msg("app.startup", message="Application started")
    yield

    # Shutdown
    log.msg("app.shutdown", message="Application shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="Job-AI-Auto-Apply Web UI API",
    description="REST API for Web UI Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions."""
    log.msg(
        "error.uncaught",
        message=str(exc),
        exc_type=type(exc).__name__,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc),
        },
    )


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/v1/health", tags=["health"])
async def api_health_check() -> Dict[str, Any]:
    """Health check for API v1."""
    return {"status": "ok", "version": "v1", "services": [
        "profiles",
        "queue",
        "settings",
        "artifacts",
        "cli",
    ]}


# API v1 routes
from src.api.routes import router as api_router
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", 5000))
    debug = os.getenv("BACKEND_DEBUG", "False").lower() == "true"

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=debug,
    )
