"""
Storage API — enterprise-documents bucket operations.

Provides endpoints to upload files, retrieve signed URLs,
list files, and delete files — all scoped to a user + case.

Every file lives at:
    users/{user_id}/{case_id}/{folder}/{filename}

No public access. Files are served via signed URLs only.

Requirements: 9.1 (auth injected via router-level Depends in main.py)
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from backend.auth.middleware.jwt_middleware import AuthContext, get_current_user
from backend.auth.services.storage_service import (
    Folder,
    delete_file,
    get_signed_url,
    list_files,
    upload_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/storage",
    tags=["File Storage"],
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    path: str
    message: str


class SignedUrlResponse(BaseModel):
    url: str
    expires_in: int


class FileListResponse(BaseModel):
    files: list[dict]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{case_id}/{folder}",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload a file for a case",
)
async def upload(
    case_id: str,
    folder: Folder,
    file: UploadFile = File(...),
    auth: AuthContext = Depends(get_current_user),
):
    """
    Upload a file into users/{user_id}/{case_id}/{folder}/.

    - `folder` must be one of: uploads, reports, graphs, cache
    - Requires valid JWT (injected by router-level dependency in main.py)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename.")

    data = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        path = await upload_file(
            user_id=auth.user_id,
            case_id=case_id,
            folder=folder,
            filename=file.filename,
            data=data,
            content_type=content_type,
        )
    except RuntimeError as exc:
        logger.error("Upload failed for user=%s case=%s: %s", auth.user_id, case_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return UploadResponse(path=path, message="File uploaded successfully.")


@router.get(
    "/{case_id}/{folder}/{filename}/url",
    response_model=SignedUrlResponse,
    summary="Get a signed URL for a file",
)
async def signed_url(
    case_id: str,
    folder: Folder,
    filename: str,
    expires_in: Annotated[int, Query(ge=60, le=86400)] = 3600,
    auth: AuthContext = Depends(get_current_user),
):
    """
    Generate a time-limited signed URL for private file access.

    - `expires_in`: seconds until expiry (60–86400, default 3600)
    - Only the owning user can generate a URL for their own files.
    """
    try:
        url = await get_signed_url(
            user_id=auth.user_id,
            case_id=case_id,
            folder=folder,
            filename=filename,
            expires_in=expires_in,
        )
    except RuntimeError as exc:
        logger.error("Signed URL failed for user=%s: %s", auth.user_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SignedUrlResponse(url=url, expires_in=expires_in)


@router.get(
    "/{case_id}/{folder}",
    response_model=FileListResponse,
    summary="List files in a folder",
)
async def list_case_files(
    case_id: str,
    folder: Folder,
    auth: AuthContext = Depends(get_current_user),
):
    """
    List all files in users/{user_id}/{case_id}/{folder}/.
    """
    try:
        files = await list_files(
            user_id=auth.user_id,
            case_id=case_id,
            folder=folder,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileListResponse(files=files)


@router.delete(
    "/{case_id}/{folder}/{filename}",
    status_code=204,
    summary="Delete a file",
)
async def remove_file(
    case_id: str,
    folder: Folder,
    filename: str,
    auth: AuthContext = Depends(get_current_user),
):
    """
    Delete a file from users/{user_id}/{case_id}/{folder}/{filename}.
    Returns 204 No Content on success.
    """
    try:
        await delete_file(
            user_id=auth.user_id,
            case_id=case_id,
            folder=folder,
            filename=filename,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
