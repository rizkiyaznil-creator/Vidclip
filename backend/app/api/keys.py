"""Route pengelolaan API key user (BYOK), disimpan terenkripsi."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import encrypt_secret, mask_secret
from app.db import get_db
from app.models import ApiKey, Provider, User
from app.schemas.keys import ApiKeyCreate, ApiKeyOut

router = APIRouter(prefix="/keys", tags=["api-keys"])


@router.put("", response_model=ApiKeyOut)
def upsert_key(
    payload: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKey:
    """Simpan/ganti API key untuk satu provider (satu key per provider per user)."""
    key = db.scalar(
        select(ApiKey).where(
            ApiKey.user_id == current_user.id, ApiKey.provider == payload.provider
        )
    )
    if key is None:
        key = ApiKey(user_id=current_user.id, provider=payload.provider)
        db.add(key)
    key.ciphertext = encrypt_secret(payload.api_key)
    key.hint = mask_secret(payload.api_key)
    db.commit()
    db.refresh(key)
    return key


@router.get("", response_model=list[ApiKeyOut])
def list_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiKey]:
    return list(
        db.scalars(select(ApiKey).where(ApiKey.user_id == current_user.id)).all()
    )


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def delete_key(
    provider: Provider,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    key = db.scalar(
        select(ApiKey).where(
            ApiKey.user_id == current_user.id, ApiKey.provider == provider
        )
    )
    if key is not None:
        db.delete(key)
        db.commit()
