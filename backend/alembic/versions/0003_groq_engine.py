"""tambah provider groq & kolom transcribe_engine

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tambah nilai 'groq' ke enum provider (idempoten).
    op.execute("ALTER TYPE provider ADD VALUE IF NOT EXISTS 'groq'")
    op.add_column(
        "jobs",
        sa.Column(
            "transcribe_engine",
            sa.String(length=32),
            nullable=False,
            server_default="openai",
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "transcribe_engine")
    # Catatan: PostgreSQL tidak mendukung penghapusan nilai enum; 'groq' dibiarkan.
