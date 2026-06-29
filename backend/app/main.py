"""Entry point aplikasi FastAPI Vidclip."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api import auth, health, jobs, keys
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Vidclip API",
    version=__version__,
    debug=settings.app_debug,
)

# CORS — longgar saat dev; perketat di produksi.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(jobs.router)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")


# Frontend statis (single-page). Disajikan di /app.
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/app", StaticFiles(directory=_static_dir, html=True), name="frontend")
