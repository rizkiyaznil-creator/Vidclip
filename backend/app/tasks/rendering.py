"""Task: render klip terpilih (potong + reframe 9:16 + subtitle)."""

import os
import tempfile
import uuid

from app.celery_app import celery_app
from app.config import get_settings
from app.core import storage
from app.db import SessionLocal
from app.models import Clip, ClipStatus, Job, JobStatus
from app.services.render import render_clip
from app.services.transcribe.base import Transcript


def run_rendering(job_id: str, reframe_method: str | None = None) -> None:
    settings = get_settings()
    method = reframe_method or settings.reframe_method
    db = SessionLocal()
    tmpdir = tempfile.mkdtemp(prefix="vidclip-render-")
    try:
        job = db.get(Job, uuid.UUID(job_id))
        if job is None:
            return
        clips = [c for c in job.clips if c.selected]
        if not clips:
            return

        job.status = JobStatus.rendering
        db.commit()

        ext = os.path.splitext(job.source_key or "")[1] or ".mp4"
        video_path = os.path.join(tmpdir, f"source{ext}")
        storage.download_file(job.source_key, video_path)

        words = Transcript.from_dict(job.transcript or {}).words

        for clip in clips:
            try:
                clip.status = ClipStatus.rendering
                db.commit()
                out_path = os.path.join(tmpdir, f"{clip.id}.mp4")
                render_clip(
                    video_path, out_path,
                    clip.start_sec, clip.end_sec, words,
                    method=method, preset=clip.subtitle_preset,
                )
                key = f"clips/{job.id}/{clip.id}.mp4"
                storage.upload_file(out_path, key, content_type="video/mp4")
                clip.output_key = key
                clip.status = ClipStatus.done
                db.commit()
            except Exception as exc:  # noqa: BLE001 - tandai klip gagal, lanjut
                db.rollback()
                clip = db.get(Clip, clip.id)
                if clip is not None:
                    clip.status = ClipStatus.failed
                    db.commit()
                _log_clip_error(clip, exc)

        job = db.get(Job, uuid.UUID(job_id))
        job.status = JobStatus.done
        db.commit()
    finally:
        db.close()
        _cleanup(tmpdir)


def _log_clip_error(clip, exc) -> None:
    import logging

    logging.getLogger("vidclip.render").error("Klip gagal dirender: %s", exc)


def _cleanup(path: str) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


@celery_app.task(name="vidclip.render_job")
def render_job(job_id: str, reframe_method: str | None = None) -> None:
    run_rendering(job_id, reframe_method)


__all__ = ["run_rendering", "render_job"]
