"""Task pemeliharaan: auto-hapus job & file lama (retensi)."""

from datetime import UTC, datetime, timedelta

from app.celery_app import celery_app
from app.config import get_settings
from app.core import storage
from app.db import SessionLocal
from app.models import Job


def run_cleanup() -> int:
    """Hapus job (beserta file storage) yang lebih tua dari retention_days.
    Kembalikan jumlah job yang dihapus."""
    settings = get_settings()
    cutoff = datetime.now(tz=UTC) - timedelta(days=settings.retention_days)
    db = SessionLocal()
    removed = 0
    try:
        old_jobs = db.query(Job).filter(Job.created_at < cutoff).all()
        for job in old_jobs:
            for prefix in (f"raw/{job.id}/", f"clips/{job.id}/"):
                try:
                    storage.delete_prefix(prefix)
                except Exception:  # noqa: BLE001
                    pass
            db.delete(job)
            removed += 1
        db.commit()
    finally:
        db.close()
    return removed


@celery_app.task(name="vidclip.cleanup_old_jobs")
def cleanup_old_jobs() -> int:
    return run_cleanup()


__all__ = ["run_cleanup", "cleanup_old_jobs"]
