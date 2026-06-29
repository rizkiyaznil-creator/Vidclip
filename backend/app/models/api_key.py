"""Model ApiKey — menyimpan API key user (BYOK) dalam bentuk terenkripsi."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Provider(str, enum.Enum):
    openai = "openai"
    anthropic = "anthropic"


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_apikey_user_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[Provider] = mapped_column(Enum(Provider, name="provider"), nullable=False)
    # Key user, dienkripsi dengan Fernet. Tidak pernah disimpan plaintext.
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Petunjuk yang aman ditampilkan (mis. "sk-…ab12"), bukan key utuh.
    hint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="api_keys")  # noqa: F821
