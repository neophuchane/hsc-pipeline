"""
FastAPI application.

In production, serves the built Vite frontend as static files from ./static.
In development, the Vite dev server (port 5173) handles the frontend with HMR.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes.upload import router as upload_router
from app.routes.pipeline import router as pipeline_router
from app.routes.results import router as results_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/hsc_uploads"))
STATIC_DIR = Path(__file__).parent.parent / "static"  # built frontend


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("HSC Pipeline API started. Upload dir: %s", UPLOAD_DIR)
    yield
    logger.info("HSC Pipeline API shutting down")


app = FastAPI(
    title="HSC Developmental Stage Classification",
    version="1.0.0",
    lifespan=lifespan,
    # Hide docs in production if desired
    docs_url="/api/docs",
    redoc_url=None,
)

# CORS — allow Vite dev server during development
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (must be registered before static mount)
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(pipeline_router, prefix="/api", tags=["pipeline"])
app.include_router(results_router, prefix="/api", tags=["results"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Serve built frontend (only if the static directory exists — i.e., production build)
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        return FileResponse(str(STATIC_DIR / "index.html"))
