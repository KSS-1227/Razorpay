"""
Workspace-aware upload route.

Replaces the global upload.py for authenticated requests.
Files are saved to:
    data/users/{user_id}/cases/{case_id}/uploads/

The case_id is generated here and returned to the client.
All pipeline processing happens inside the user's workspace.

The original upload.py is NOT modified.
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.workspace import UserWorkspace
from backend.auth.services.case_service import create_case, get_case
from backend.services.workspace_document_service import WorkspaceDocumentService
from backend.storage.s3_document_storage import upload_document

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Document Upload"],
)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
    ".mp3", ".wav", ".m4a", ".flac", ".ogg",
}

_UNSAFE = re.compile(r"[^\w.\-]")


def _sanitize(name: str) -> str:
    name = Path(name).name
    name = _UNSAFE.sub("_", name)
    return name or "unnamed_file"


@router.post("/")
async def upload_documents(
    files: list[UploadFile] = File(...),
    case_id: str | None = Form(default=None),
    auth: AuthContext = Depends(get_current_user),
):
    """Upload documents into the authenticated user's workspace.

    - If case_id is provided, files are added to that existing case.
    - If case_id is omitted, a new case is created automatically.
    - Saves files to data/users/{user_id}/cases/{case_id}/uploads/
    - Runs the MMKGBuilder pipeline inside the same workspace.

    user_id is taken from the JWT — never from the request.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # Resolve or create the case
    if case_id:
        # Verify ownership — raises 404 if not found or not owned
        try:
            await get_case(case_id=case_id, user_id=auth.user_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail="Case not found.") from exc
    else:
        # Auto-create a case named after the first file
        first_name = files[0].filename or "Untitled"
        case_title = Path(first_name).stem[:100] or "Untitled"
        new_case = await create_case(
            user_id=auth.user_id,
            title=case_title,
            description=None,
        )
        case_id = new_case["id"]

    ws = UserWorkspace(user_id=auth.user_id, case_id=case_id).ensure()

    logger.info(
        "📁 New upload — user=%s case=%s files=%d",
        auth.user_id, case_id, len(files),
    )

    start = time.time()

    # ── Save files ──────────────────────────────────────────────────────
    file_results: list = []
    saved_paths:  list = []

    for upload in files:
        original_name = upload.filename or "unnamed"
        safe_name     = _sanitize(original_name)
        extension     = Path(safe_name).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            file_results.append({
                "filename": original_name,
                "status":   "skipped",
                "reason":   f"Unsupported file type '{extension}'",
            })
            continue

        destination = ws.uploads / safe_name

        # Deduplicate filenames within the same case
        if destination.exists():
            stem        = Path(safe_name).stem
            safe_name   = f"{stem}_{uuid.uuid4().hex[:6]}{extension}"
            destination = ws.uploads / safe_name

        try:
            content = await upload.read()
            destination.write_bytes(content)
            storage_key = await upload_document(
                user_id=auth.user_id,
                case_id=case_id,
                filename=safe_name,
                data=content,
                content_type=upload.content_type or "application/octet-stream",
            )
            saved_paths.append(str(destination))
            file_result = {
                "filename":   original_name,
                "stored_as":  safe_name,
                "size_bytes": destination.stat().st_size,
                "status":     "saved",
            }
            if storage_key:
                file_result["storage_key"] = storage_key
                file_result["storage_backend"] = "s3"
            else:
                file_result["storage_backend"] = "local"
            file_results.append(file_result)
            logger.info("✅ Saved %s → %s", original_name, destination)
        except Exception as exc:
            logger.error("❌ Failed to save %s: %s", original_name, exc)
            file_results.append({
                "filename": original_name,
                "status":   "failed",
                "reason":   f"Could not save file: {exc}",
            })

    if not saved_paths:
        raise HTTPException(
            status_code=400,
            detail="No supported files could be saved. Check formats and try again.",
        )

    # ── Process through workspace-scoped pipeline ────────────────────────
    svc       = WorkspaceDocumentService(user_id=auth.user_id, case_id=case_id)
    kg_result = await svc.process_documents(
        file_paths=saved_paths,
        file_results=file_results,
    )

    # Merge per-file processing status back into file_results
    processing_map = {r["file"]: r for r in kg_result.pop("file_results", [])}
    for entry in file_results:
        name = entry.get("stored_as") or entry.get("filename", "")
        if name in processing_map:
            entry["processing"] = processing_map[name].get("status", "unknown")
            if "error" in processing_map[name]:
                entry["error"] = processing_map[name]["error"]

    processing_time = round(time.time() - start, 2)

    return {
        "success":                 kg_result.get("total_processed", 0) > 0,
        "case_id":                 case_id,
        "user_id":                 auth.user_id,
        "workspace":               str(ws.root),
        "message":                 "Enterprise Knowledge Graph processing complete.",
        "files":                   file_results,
        "processing_time_seconds": processing_time,
        "knowledge_graph":         kg_result,
    }
