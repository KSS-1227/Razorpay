"""Private S3 storage for raw case documents.

The ingestion pipeline still needs a local temporary copy while it extracts
content.  This module makes S3 the durable copy when
``DOCUMENT_STORAGE_BACKEND=s3``; it never exposes public object URLs.
"""
from __future__ import annotations

import asyncio
import os
from functools import lru_cache


class S3StorageConfigurationError(RuntimeError):
    """Raised when S3 storage is selected without a usable bucket."""


def is_enabled() -> bool:
    """Return whether the explicit production S3 backend is enabled."""
    return os.environ.get("DOCUMENT_STORAGE_BACKEND", "local").lower() == "s3"


def _bucket() -> str:
    bucket = os.environ.get("S3_DOCUMENT_BUCKET", "").strip()
    if not bucket:
        raise S3StorageConfigurationError(
            "S3_DOCUMENT_BUCKET must be set when DOCUMENT_STORAGE_BACKEND=s3"
        )
    return bucket


@lru_cache(maxsize=1)
def _client():
    try:
        import boto3
    except ImportError as exc:
        raise S3StorageConfigurationError(
            "boto3 is not installed; install the project requirements before enabling S3"
        ) from exc

    return boto3.client("s3", region_name=os.environ.get("AWS_REGION") or None)


def upload_key(user_id: str, case_id: str, filename: str) -> str:
    """Return the private, tenant-scoped key for a raw document."""
    return f"users/{user_id}/cases/{case_id}/uploads/{filename}"


async def upload_document(
    *,
    user_id: str,
    case_id: str,
    filename: str,
    data: bytes,
    content_type: str,
) -> str | None:
    """Durably store one upload when S3 is enabled; otherwise return None."""
    if not is_enabled():
        return None

    bucket = _bucket()
    key = upload_key(user_id, case_id, filename)

    def _put() -> None:
        _client().put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type or "application/octet-stream",
            ServerSideEncryption="AES256",
        )

    await asyncio.to_thread(_put)
    return key


async def delete_case_documents(*, user_id: str, case_id: str) -> int:
    """Delete all raw objects for a case when S3 is enabled."""
    if not is_enabled():
        return 0

    bucket = _bucket()
    prefix = f"users/{user_id}/cases/{case_id}/"

    def _delete() -> int:
        client = _client()
        deleted = 0
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
            if not objects:
                continue
            client.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True})
            deleted += len(objects)
        return deleted

    return await asyncio.to_thread(_delete)
