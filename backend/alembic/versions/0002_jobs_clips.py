"""jobs & clips

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    job_status = postgresql.ENUM(
        "uploaded", "transcribing", "analyzing", "awaiting_review",
        "rendering", "done", "failed", name="job_status",
    )
    job_status.create(op.get_bind(), checkfirst=True)
    clip_status = postgresql.ENUM(
        "candidate", "rendering", "done", "failed", name="clip_status"
    )
    clip_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="job_status", create_type=False),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("source_key", sa.String(length=512), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("instruction", sa.String(length=1000), nullable=True),
        sa.Column("model", sa.String(length=32), nullable=False, server_default="haiku"),
        sa.Column("transcript", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])

    op.create_table(
        "clips",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("caption", sa.String(length=2000), nullable=True),
        sa.Column("hashtags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("start_sec", sa.Float(), nullable=False),
        sa.Column("end_sec", sa.Float(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "subtitle_preset", sa.String(length=32), nullable=False, server_default="classic"
        ),
        sa.Column("output_key", sa.String(length=512), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="clip_status", create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clips_job_id", "clips", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_clips_job_id", table_name="clips")
    op.drop_table("clips")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_table("jobs")
    postgresql.ENUM(name="clip_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="job_status").drop(op.get_bind(), checkfirst=True)
