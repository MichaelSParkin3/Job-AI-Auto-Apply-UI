"""FastAPI application initialization and configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Job-AI-Auto-Apply Web UI API",
    description="REST API for Web UI Dashboard",
    version="0.1.0",
)

# Configure CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/v1/health")
async def api_health_check():
    """Health check for API v1."""
    return {"status": "ok", "version": "v1"}


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
