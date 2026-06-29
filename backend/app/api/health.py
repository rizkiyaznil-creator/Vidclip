"""Endpoint healthcheck — verifikasi konektivitas DB, Redis, dan storage."""

import redis
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.core.storage import bucket_exists
from app.db import engine

router = APIRouter(tags=["health"])


def _check_db() -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def _check_redis() -> bool:
    client = redis.Redis.from_url(get_settings().redis_url)
    return bool(client.ping())


@router.get("/health")
def health() -> dict:
    """Liveness sederhana — proses hidup."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> dict:
    """Readiness — cek semua dependency siap dipakai."""
    checks: dict[str, str] = {}
    overall = True

    for name, fn in (("database", _check_db), ("redis", _check_redis), ("storage", bucket_exists)):
        try:
            fn()
            checks[name] = "ok"
        except Exception as exc:  # noqa: BLE001 - laporkan apa adanya di healthcheck
            checks[name] = f"error: {exc}"
            overall = False

    return {"status": "ready" if overall else "degraded", "checks": checks}
