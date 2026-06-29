"""Entry point aplikasi FastAPI Vidclip."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
def root() -> dict:
    return {"app": "Vidclip", "version": __version__, "docs": "/docs"}
