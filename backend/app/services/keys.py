"""Akses API key user yang terdekripsi (dipakai worker, hanya di memori)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret
from app.models import ApiKey, Provider


class MissingApiKeyError(RuntimeError):
    def __init__(self, provider: Provider):
        self.provider = provider
        super().__init__(f"API key untuk '{provider.value}' belum diatur.")


def get_decrypted_key(db: Session, user_id: uuid.UUID, provider: Provider) -> str:
    row = db.scalar(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.provider == provider)
    )
    if row is None:
        raise MissingApiKeyError(provider)
    return decrypt_secret(row.ciphertext)
