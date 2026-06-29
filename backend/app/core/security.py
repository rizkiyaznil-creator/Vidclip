"""Primitif keamanan: hashing password, JWT, dan enkripsi API key (Fernet)."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()
ALGORITHM = "HS256"


# ─── Password hashing (bcrypt) ─────────────────────────────
def hash_password(plain: str) -> str:
    # bcrypt membatasi input 72 byte; cukup untuk password.
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        return False


# ─── JWT ───────────────────────────────────────────────────
def create_access_token(subject: str) -> str:
    expire = datetime.now(tz=UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(subject), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode & verifikasi JWT. Melempar jwt.PyJWTError bila tidak valid/kadaluarsa."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


# ─── Enkripsi API key user (Fernet, simetris) ──────────────
def _fernet() -> Fernet:
    return Fernet(settings.master_encryption_key.encode())


def encrypt_secret(plaintext: str) -> bytes:
    """Enkripsi rahasia (API key user) untuk disimpan at-rest."""
    return _fernet().encrypt(plaintext.encode())


def decrypt_secret(ciphertext: bytes) -> str:
    """Dekripsi rahasia kembali ke plaintext (hanya di memori, sesaat)."""
    return _fernet().decrypt(ciphertext).decode()


def mask_secret(plaintext: str) -> str:
    """Hint aman untuk ditampilkan ke user (tidak pernah key utuh)."""
    if len(plaintext) <= 7:
        return "••••"
    return f"{plaintext[:3]}…{plaintext[-4:]}"
