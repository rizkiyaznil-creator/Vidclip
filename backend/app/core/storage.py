"""Abstraksi object storage (S3-compatible: MinIO / S3 / R2)."""

from functools import lru_cache
from typing import BinaryIO

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
    get_s3_client().head_bucket(Bucket=settings.s3_bucket)
    return True


def upload_fileobj(fileobj: BinaryIO, key: str, content_type: str | None = None) -> str:
    """Unggah file-like ke storage, kembalikan key-nya."""
    settings = get_settings()
    extra = {"ContentType": content_type} if content_type else {}
    get_s3_client().upload_fileobj(fileobj, settings.s3_bucket, key, ExtraArgs=extra)
    return key


def upload_file(local_path: str, key: str, content_type: str | None = None) -> str:
    """Unggah file dari path lokal ke storage."""
    settings = get_settings()
    extra = {"ContentType": content_type} if content_type else {}
    get_s3_client().upload_file(local_path, settings.s3_bucket, key, ExtraArgs=extra)
    return key


def download_file(key: str, local_path: str) -> str:
    """Unduh objek dari storage ke path lokal."""
    settings = get_settings()
    get_s3_client().download_file(settings.s3_bucket, key, local_path)
    return local_path


def presigned_url(key: str, expires: int = 3600) -> str:
    """URL sementara untuk mengunduh objek (dipakai frontend)."""
    settings = get_settings()
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires,
    )


def delete_prefix(prefix: str) -> None:
    """Hapus semua objek dengan prefix tertentu (mis. saat job dibatalkan)."""
    settings = get_settings()
    client = get_s3_client()
    resp = client.list_objects_v2(Bucket=settings.s3_bucket, Prefix=prefix)
    objs = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
    if objs:
        client.delete_objects(Bucket=settings.s3_bucket, Delete={"Objects": objs})
