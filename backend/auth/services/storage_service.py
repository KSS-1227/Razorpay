"""
Storage service — manages file operations in the `enterprise-documents` bucket.

Folder structure:
    users/{user_id}/{case_id}/uploads/   — raw uploaded documents
    users/{user_id}/{case_id}/reports/   — generated compliance reports
    users/{user_id}/{case_id}/graphs/    — knowledge graph artefacts
    users/{user_id}/{case_id}/cache/     — intermediate pipeline cache

Every path is scoped to a user_id + case_id pair.
No files are publicly accessible — access is via signed URLs only.
"""
from __future__ import annotations

import logging
from enum import Enum

from ..supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

BUCKET = "enterprise-documents"

# Signed URL expiry in seconds (default: 1 hour)
SIGNED_URL_EXPIRY = 3600


class Folder(str, Enum):
    UPLOADS = "uploads"
    REPORTS = "reports"
    GRAPHS  = "graphs"
    CACHE   = "cache"


def build_path(user_id: str, case_id: str, folder: Folder, filename: str) -> str:
    """
    Construct the canonical storage path for a file.

    Pattern: users/{user_id}/{case_id}/{folder}/{filename}
    """
    return f"users/{user_id}/{case_id}/{folder.value}/{filename}"


async def upload_file(
    user_id: str,
    case_id: str,
    folder: Folder,
    filename: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload a file to the enterprise-documents bucket.

    Returns the storage path on success.
    Raises on failure.
    """
    client = await get_supabase_client()
    path = build_path(user_id, case_id, folder, filename)

    response = await client.storage.from_(BUCKET).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Upload failed: {response.error}")

    logger.info("Uploaded file to %s/%s", BUCKET, path)
    return path


async def get_signed_url(
    user_id: str,
    case_id: str,
    folder: Folder,
    filename: str,
    expires_in: int = SIGNED_URL_EXPIRY,
) -> str:
    """
    Generate a signed URL for temporary access to a private file.

    expires_in: seconds until the URL expires (default 3600 = 1 hour)
    Returns the signed URL string.
    """
    client = await get_supabase_client()
    path = build_path(user_id, case_id, folder, filename)

    response = await client.storage.from_(BUCKET).create_signed_url(
        path=path,
        expires_in=expires_in,
    )

    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Failed to generate signed URL: {response.error}")

    # supabase-py v2 returns the URL under 'signedUrl' (camelCase)
    data = response.data if hasattr(response, "data") else response
    if isinstance(data, dict):
        signed_url = data.get("signedUrl") or data.get("signedURL")
    else:
        signed_url = getattr(data, "signed_url", None) or getattr(data, "signedUrl", None)

    if not signed_url:
        raise RuntimeError("Signed URL not found in Supabase response")

    return signed_url


async def delete_file(
    user_id: str,
    case_id: str,
    folder: Folder,
    filename: str,
) -> None:
    """
    Delete a file from storage. Raises on failure.
    """
    client = await get_supabase_client()
    path = build_path(user_id, case_id, folder, filename)

    response = await client.storage.from_(BUCKET).remove([path])

    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Delete failed: {response.error}")

    logger.info("Deleted file %s/%s", BUCKET, path)


async def list_files(
    user_id: str,
    case_id: str,
    folder: Folder,
) -> list[dict]:
    """
    List all files in a specific folder for a user/case pair.
    Returns a list of file metadata dicts.
    """
    client = await get_supabase_client()
    prefix = f"users/{user_id}/{case_id}/{folder.value}"

    response = await client.storage.from_(BUCKET).list(path=prefix)

    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"List failed: {response.error}")

    return response if isinstance(response, list) else []
