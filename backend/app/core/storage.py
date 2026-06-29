"""Abstraksi object storage (S3-compatible: MinIO / S3 / R2)."""

from functools import lru_cache

import boto3
from botocore.client import Config

from app.config import get_settings


@lru_cache
def get_s3_client():
    """Client boto3 untuk object storage. Di-cache (thread-safe untuk read)."""
    settings = get_settings()
    addressing = "path" if settings.s3_use_path_style else "virtual"
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(s3={"addressing_style": addressing}),
    )


def bucket_exists() -> bool:
    """Cek apakah bucket konfigurasi dapat diakses (untuk healthcheck)."""
    settings = get_settings()
    client = get_s3_client()
    client.head_bucket(Bucket=settings.s3_bucket)
    return True
