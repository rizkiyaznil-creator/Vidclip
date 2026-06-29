"""Instance Celery untuk pemrosesan video di background."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "vidclip",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.processing", "app.tasks.rendering", "app.tasks.maintenance"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_max_tasks_per_child=20,  # cegah kebocoran memori dari ffmpeg/opencv
    beat_schedule={
        "cleanup-old-jobs": {
            "task": "vidclip.cleanup_old_jobs",
            "schedule": 3600.0,  # tiap jam, hapus job > retention_days
        }
    },
)
