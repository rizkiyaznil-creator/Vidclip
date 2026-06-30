"""Schema untuk Job & Clip."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.clip import ClipStatus
from app.models.job import JobStatus


class ClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    score: int
    reason: str | None
    caption: str | None
    hashtags: list[str] | None
    start_sec: float
    end_sec: float
    selected: bool
    subtitle_preset: str
    status: ClipStatus
    output_key: str | None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: JobStatus
    filename: str | None
    language: str | None
    instruction: str | None
    model: str
    transcribe_engine: str
    error: str | None
    created_at: datetime


class JobDetail(JobOut):
    clips: list[ClipOut] = []


class ClipUpdate(BaseModel):
    selected: bool | None = None
    subtitle_preset: str | None = None
