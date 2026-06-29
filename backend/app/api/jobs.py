"""Route Job & Clip: upload, status, review, render, download."""

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import storage
from app.db import get_db
from app.models import Clip, ClipStatus, Job, JobStatus, User
from app.schemas.jobs import ClipUpdate, JobDetail, JobOut
from app.services.subtitle import PRESETS

router = APIRouter(tags=["jobs"])

ALLOWED_MODELS = {"haiku", "opus"}


def _enqueue_process(job_id: str) -> None:
    from app.tasks.processing import process_job

    process_job.delay(job_id)


def _enqueue_render(job_id: str) -> None:
    from app.tasks.rendering import render_job

    render_job.delay(job_id)


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    instruction: str | None = Form(None),
    model: str = Form("haiku"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    if file.content_type and not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File harus berupa video.")
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail="Model harus 'haiku' atau 'opus'.")

    job_id = uuid.uuid4()
    ext = os.path.splitext(file.filename or "")[1].lower() or ".mp4"
    source_key = f"raw/{job_id}/source{ext}"
    storage.upload_fileobj(file.file, source_key, content_type=file.content_type)

    job = Job(
        id=job_id,
        user_id=current_user.id,
        status=JobStatus.uploaded,
        filename=file.filename,
        source_key=source_key,
        language=language or None,
        instruction=instruction or None,
        model=model,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _enqueue_process(str(job.id))
    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Job]:
    return list(
        db.scalars(
            select(Job).where(Job.user_id == current_user.id).order_by(Job.created_at.desc())
        ).all()
    )


def _get_owned_job(db: Session, user: User, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
    return job


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    return _get_owned_job(db, current_user, job_id)


@router.post("/jobs/{job_id}/render", response_model=JobDetail)
def render(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    job = _get_owned_job(db, current_user, job_id)
    if job.status not in (JobStatus.awaiting_review, JobStatus.done):
        raise HTTPException(status_code=409, detail="Job belum siap dirender.")
    if not any(c.selected for c in job.clips):
        raise HTTPException(status_code=400, detail="Pilih minimal satu klip dulu.")
    _enqueue_render(str(job.id))
    return job


def _get_owned_clip(db: Session, user: User, clip_id: uuid.UUID) -> Clip:
    clip = db.get(Clip, clip_id)
    if clip is None or clip.job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Klip tidak ditemukan.")
    return clip


@router.patch("/clips/{clip_id}")
def update_clip(
    clip_id: uuid.UUID,
    payload: ClipUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    clip = _get_owned_clip(db, current_user, clip_id)
    if payload.selected is not None:
        clip.selected = payload.selected
    if payload.subtitle_preset is not None:
        if payload.subtitle_preset not in PRESETS:
            raise HTTPException(status_code=400, detail="Preset subtitle tidak dikenal.")
        clip.subtitle_preset = payload.subtitle_preset
    db.commit()
    return {"ok": True, "selected": clip.selected, "subtitle_preset": clip.subtitle_preset}


@router.get("/clips/{clip_id}/download")
def download_clip(
    clip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    clip = _get_owned_clip(db, current_user, clip_id)
    if clip.status != ClipStatus.done or not clip.output_key:
        raise HTTPException(status_code=409, detail="Klip belum selesai dirender.")
    return {"url": storage.presigned_url(clip.output_key)}


@router.get("/presets")
def list_presets() -> dict:
    """Daftar preset subtitle yang tersedia (untuk dropdown di UI)."""
    return {"presets": list(PRESETS.keys())}
