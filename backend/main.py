"""
BillSplit AI — FastAPI Application Entry Point

Startup order:
  1. Load .env
  2. Create FastAPI app with metadata for Swagger
  3. Add CORS middleware (all origins in dev; restrict in prod)
  4. Mount API routers
  5. Serve frontend static files at /
  6. Health check at /health

Run with:
  cd billsplit-ai/backend
  uvicorn main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs
Frontend:   http://localhost:8000
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path so 'backend.*' imports resolve cleanly
_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env before anything else
load_dotenv(Path(__file__).parent / ".env")

from backend.api import bill as bill_router  # noqa: E402
from backend.api import split as split_router  # noqa: E402

app = FastAPI(
    title="BillSplit AI",
    description=(
        "Upload a bill photograph → AI extracts structured items → "
        "human review → assign items to people → proportional split calculation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow all origins in development. In production, restrict to your domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(bill_router.router)
app.include_router(split_router.router)


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health() -> dict:
    """Quick liveness probe."""
    return {"status": "ok", "service": "BillSplit AI"}


# ── Frontend Static Files ─────────────────────────────────────────────────────
_frontend = Path(__file__).parent.parent / "frontend"

if _frontend.exists():
    # Serve static assets (CSS, JS)
    app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(str(_frontend / "index.html"))

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str) -> FileResponse:
        """Catch-all: serve index.html for any non-API route."""
        requested = _frontend / path
        if requested.exists() and requested.is_file():
            return FileResponse(str(requested))
        return FileResponse(str(_frontend / "index.html"))
