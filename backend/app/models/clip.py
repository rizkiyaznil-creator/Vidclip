"""Model Clip — satu kandidat/hasil potongan klip dari sebuah Job."""

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ClipStatus(str, enum.Enum):
    candidate = "candidate"
    rendering = "rendering"
    done = "done"
    failed = "failed"


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000))
    caption: Mapped[str | None] = mapped_column(String(2000))
    hashtags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subtitle_preset: Mapped[str] = mapped_column(String(32), default="classic", nullable=False)
    output_key: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[ClipStatus] = mapped_column(
        Enum(ClipStatus, name="clip_status"), default=ClipStatus.candidate, nullable=False
    )

    job: Mapped["Job"] = relationship(back_populates="clips")  # noqa: F821
