"""Konfigurasi aplikasi, dibaca dari environment variable / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_env: str = "development"
    app_debug: bool = True

    # Database
    database_url: str = "postgresql+psycopg://vidclip:vidclip@localhost:5432/vidclip"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Object storage (S3-compatible)
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "vidclip"
    s3_region: str = "us-east-1"
    s3_use_path_style: bool = True

    # Security
    jwt_secret: str = "change-me-in-production"
    jwt_expire_minutes: int = 10080
    master_encryption_key: str = "change-me-generate-a-real-fernet-key"

    # Pemrosesan video
    # Metode reframe default ke 9:16: 'face' (ikuti wajah) | 'blur' | 'crop'.
    # 'face' otomatis fallback ke 'blur' bila wajah tak terdeteksi/mediapipe absen.
    reframe_method: str = "face"
    max_upload_mb: int = 1024  # batas ukuran upload (default 1 GB)


@lru_cache
def get_settings() -> Settings:
    """Singleton settings (di-cache supaya .env hanya dibaca sekali)."""
    return Settings()
