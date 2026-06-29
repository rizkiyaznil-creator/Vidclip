"""Model Job — satu video yang diproses menjadi klip-klip."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class JobStatus(str, enum.Enum):
    uploaded = "uploaded"
    transcribing = "transcribing"
    analyzing = "analyzing"
    awaiting_review = "awaiting_review"
    rendering = "rendering"
    done = "done"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.uploaded, nullable=False
    )
    filename: Mapped[str | None] = mapped_column(String(512))
    source_key: Mapped[str | None] = mapped_column(String(512))
    language: Mapped[str | None] = mapped_column(String(16))
    instruction: Mapped[str | None] = mapped_column(String(1000))
    # Pilihan model AI user: 'haiku' (hemat, default) atau 'opus' (kualitas).
    model: Mapped[str] = mapped_column(String(32), default="haiku", nullable=False)
    # Transkrip lengkap (kata + timestamp) disimpan sebagai JSONB.
    transcript: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    clips: Mapped[list["Clip"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan", order_by="Clip.start_sec"
    )
