"""FastAPI application for Job-AI-Auto-Apply Web UI."""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import web_settings
from .routes import apply, discover, profiles, websockets

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(
        "Starting FastAPI server",
        profiles_dir=web_settings.profiles_dir,
        queues_dir=web_settings.queues_dir,
        artifacts_dir=web_settings.artifacts_dir,
    )

    # Validate and create necessary directories
    Path(web_settings.profiles_dir).mkdir(parents=True, exist_ok=True)
    Path(web_settings.queues_dir).mkdir(parents=True, exist_ok=True)
    Path(web_settings.artifacts_dir).mkdir(parents=True, exist_ok=True)

    logger.info("Directories validated")

    yield

    logger.info("Shutting down FastAPI server")


app = FastAPI(
    title="Job Auto Apply Web UI",
    version="0.1.0",
    description="Web UI for discovering and applying to job postings automatically",
    lifespan=lifespan,
)

# CORS middleware for development (Vite runs on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(profiles.router, prefix="/api", tags=["profiles"])
app.include_router(discover.router, prefix="/api", tags=["discover"])
app.include_router(apply.router, prefix="/api", tags=["apply"])
app.include_router(websockets.router, prefix="/ws", tags=["websockets"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "profiles_dir": web_settings.profiles_dir,
        "queues_dir": web_settings.queues_dir,
    }


def main():
    """Entry point for auto-apply-web command."""
    import uvicorn

    uvicorn.run(
        "web_ui.backend.app:app",
        host=web_settings.host,
        port=web_settings.port,
        reload=web_settings.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
