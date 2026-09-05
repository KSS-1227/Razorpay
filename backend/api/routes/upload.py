"""
Upload API — Enterprise Multi-Document Upload

Accepts one or more files, groups them under a unique case_id,
stores them in data/uploads/<case_id>/, and kicks off the
MMGraphRAG pipeline via MultiDocumentService.

Supported formats: PDF, DOCX, XLSX/XLS, PNG/JPG/JPEG/WEBP/BMP/TIFF,
                   MP3/WAV/M4A/FLAC/OGG
"""

import logging
import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.services.multidocument_service import MultiDocumentService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Document Upload"],
)

UPLOAD_BASE = Path("data/uploads")
UPLOAD_BASE.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx",
    # Spreadsheets
    ".xlsx", ".xls",
    # Images
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff",
    # Audio
    ".mp3", ".wav", ".m4a", ".flac", ".ogg",
}

# Only allow safe filename characters; replace everything else with _
_UNSAFE = re.compile(r"[^\w.\-]")


def _sanitize_filename(name: str) -> str:
    """Strip path components and replace unsafe characters."""
    name = Path(name).name          # strip any directory prefix
    name = _UNSAFE.sub("_", name)   # replace unsafe chars
    return name or "unnamed_file"


@router.post("/")
async def upload_documents(
    files: list[UploadFile] = File(...),
):
    """
    Upload one or more enterprise documents.

    - Generates a unique **case_id** for this upload session.
    - Stores all files under ``data/uploads/<case_id>/``.
    - Processes all files into a single unified Knowledge Graph.
    - Continues even if individual files fail.

    Returns per-file status, processing time, and graph summary.
    """

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # ----------------------------------------------------------------
    # Case directory
    # ----------------------------------------------------------------
    case_id  = str(uuid.uuid4())
    case_dir = UPLOAD_BASE / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 New upload session — case_id={case_id}, files={len(files)}")

    start = time.time()

    # ----------------------------------------------------------------
    # Save files
    # ----------------------------------------------------------------
    file_results: list = []
    saved_paths:  list = []

    for upload in files:
        original_name = upload.filename or "unnamed"
        safe_name     = _sanitize_filename(original_name)
        extension     = Path(safe_name).suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            logger.warning(f"⚠️  Unsupported type skipped: {original_name}")
            file_results.append({
                "filename": original_name,
                "status":   "skipped",
                "reason":   f"Unsupported file type '{extension}'",
            })
            continue

        destination = case_dir / safe_name

        # Handle duplicate filenames within the same case
        if destination.exists():
            stem      = Path(safe_name).stem
            unique    = f"{stem}_{uuid.uuid4().hex[:6]}{extension}"
            destination = case_dir / unique
            safe_name   = unique

        try:
            with destination.open("wb") as buf:
                shutil.copyfileobj(upload.file, buf)

            saved_paths.append(str(destination))
            file_results.append({
                "filename":   original_name,
                "stored_as":  safe_name,
                "size_bytes": destination.stat().st_size,
                "status":     "saved",
            })
            logger.info(f"✅ Saved: {safe_name}")

        except Exception as exc:
            logger.error(f"❌ Failed to save {original_name}: {exc}")
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

    # ----------------------------------------------------------------
    # Process through MMGraphRAG pipeline
    # ----------------------------------------------------------------
    service   = MultiDocumentService()
    kg_result = await service.process_documents(
        file_paths=saved_paths,
        case_id=case_id,
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
        "success":                  kg_result.get("total_processed", 0) > 0,
        "case_id":                  case_id,
        "message":                  "Enterprise Knowledge Graph processing complete.",
        "files":                    file_results,
        "processing_time_seconds":  processing_time,
        "knowledge_graph":          kg_result,
    }
