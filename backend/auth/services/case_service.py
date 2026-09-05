"""
Case service — database and filesystem operations for the cases resource.

Each case owns a user-scoped workspace directory:
    data/users/{user_id}/cases/{case_id}/
        uploads/   — raw uploaded documents
        working/   — intermediate pipeline artefacts
        output/    — knowledge graph + report
        cache/     — LLM response cache

Deleting a case removes the entire workspace tree AND the Supabase
Storage folder users/{user_id}/{case_id}/.

Rule: user_id is ALWAYS sourced from the validated JWT. Never from caller input.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException

from backend.auth.supabase_client import get_supabase_client
from backend.auth.workspace import UserWorkspace

logger = logging.getLogger(__name__)

STORAGE_BUCKET = "enterprise-documents"


async def _delete_storage_folder(user_id: str, case_id: str) -> None:
    """Remove all Supabase Storage objects under users/{user_id}/{case_id}/."""
    prefix = f"users/{user_id}/{case_id}"
    try:
        supabase = await get_supabase_client()
        # List all objects under the prefix
        list_resp = await supabase.storage.from_(STORAGE_BUCKET).list(path=prefix)
        files = list_resp if isinstance(list_resp, list) else []

        if files:
            paths = [f"{prefix}/{f['name']}" for f in files if f.get("name")]
            if paths:
                await supabase.storage.from_(STORAGE_BUCKET).remove(paths)
                logger.info(
                    "Deleted %d storage objects under %s/%s",
                    len(paths), STORAGE_BUCKET, prefix,
                )
    except Exception as exc:
        # Storage deletion failure must not block the DB deletion
        logger.error(
            "Storage cleanup failed for user=%s case=%s: %s", user_id, case_id, exc
        )


async def _delete_s3_documents(user_id: str, case_id: str) -> None:
    """Remove durable S3 documents when the optional S3 backend is enabled."""
    try:
        from backend.storage.s3_document_storage import delete_case_documents

        deleted = await delete_case_documents(user_id=user_id, case_id=case_id)
        if deleted:
            logger.info("Deleted %d S3 document(s) for case=%s", deleted, case_id)
    except Exception as exc:
        logger.error("S3 cleanup failed for user=%s case=%s: %s", user_id, case_id, exc)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def create_case(user_id: str, title: str, description: str | None) -> dict:
    """Create a new case record in public.cases.

    Parameters
    ----------
    user_id:
        From the validated JWT — never from caller input.
    title:
        3–200 character case title.
    description:
        Optional free-text description.

    Returns
    -------
    dict
        The created case row.

    Raises
    ------
    HTTPException 422
        Title is empty or exceeds 200 characters.
    HTTPException 503
        Database error.
    """
    title = title.strip()
    if not title or len(title) > 200:
        raise HTTPException(
            status_code=422,
            detail={"error": "validation_error", "message": "Title must be 1–200 characters"},
        )

    case_id = str(uuid.uuid4())
    payload = {
        "id":          case_id,
        "user_id":     user_id,           # always from JWT
        "title":       title,
        "description": description or "",
        "status":      "processing",
    }

    try:
        supabase = await get_supabase_client()
        result = (
            await supabase
            .from_("cases")
            .insert(payload)
            .select()
            .execute()
        )
        rows = result.data
        if not rows:
            raise RuntimeError("Insert returned no rows")
        return rows[0]
    except Exception as exc:
        logger.error("create_case failed for user=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "service_unavailable", "message": "Could not create case"},
        ) from exc


async def list_cases(user_id: str) -> list[dict]:
    """Return all cases belonging to user_id, newest first."""
    try:
        supabase = await get_supabase_client()
        result = (
            await supabase
            .from_("cases")
            .select("id, title, description, status, created_at, updated_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.error("list_cases failed for user=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "service_unavailable", "message": "Could not retrieve cases"},
        ) from exc


async def get_case(case_id: str, user_id: str) -> dict:
    """Fetch a single case, verifying ownership.

    Raises HTTPException 404 if not found or not owned by user_id.
    """
    try:
        supabase = await get_supabase_client()
        result = (
            await supabase
            .from_("cases")
            .select("*")
            .eq("id", case_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        case = result.data if result is not None else None
    except Exception as exc:
        logger.error("get_case failed for user=%s case=%s: %s", user_id, case_id, exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "service_unavailable"},
        ) from exc

    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "case_not_found", "message": "Case not found"},
        )
    return case


async def update_case(
    case_id: str,
    user_id: str,
    title: str | None,
    description: str | None,
) -> dict:
    """Partial update of a case's title and/or description.

    Only provided fields are updated (PATCH semantics).
    Ownership is verified before any write.

    Raises
    ------
    HTTPException 422
        Title exceeds 200 characters.
    HTTPException 404
        Case not found or not owned by user_id.
    """
    patch: dict = {}

    if title is not None:
        title = title.strip()
        if not title or len(title) > 200:
            raise HTTPException(
                status_code=422,
                detail={"error": "validation_error", "message": "Title must be 1–200 characters"},
            )
        patch["title"] = title

    if description is not None:
        patch["description"] = description

    if not patch:
        # Nothing to update — return current state
        return await get_case(case_id, user_id)

    try:
        supabase = await get_supabase_client()
        result = (
            await supabase
            .from_("cases")
            .update(patch)
            .eq("id", case_id)
            .eq("user_id", user_id)           # ownership enforced from JWT
            .select()
            .maybe_single()
            .execute()
        )
        updated = result.data
    except Exception as exc:
        logger.error("update_case failed for user=%s case=%s: %s", user_id, case_id, exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "service_unavailable"},
        ) from exc

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "case_not_found", "message": "Case not found"},
        )
    return updated


async def delete_case(case_id: str, user_id: str) -> dict:
    """Delete a case and ALL associated data atomically.

    Order of operations:
    1. Verify ownership (raises 404 if not found)
    2. Delete local filesystem directories (best-effort)
    3. Delete Supabase Storage objects (best-effort)
    4. Delete the DB row

    The DB row is deleted last — if filesystem/storage cleanup fails,
    the case record is still removed so the user is not left with a
    dangling record pointing to cleaned-up data.

    Returns
    -------
    dict
        Cleanup summary including filesystem and storage results.
    """
    # 1. Verify ownership first
    await get_case(case_id, user_id)

    # 2. Local filesystem cleanup via UserWorkspace
    ws = UserWorkspace(user_id=user_id, case_id=case_id)
    fs_results = ws.delete()

    # 3. Durable object-storage cleanup (best-effort)
    await _delete_storage_folder(user_id, case_id)
    await _delete_s3_documents(user_id, case_id)

    # 4. Delete DB row
    try:
        supabase = await get_supabase_client()
        await (
            supabase
            .from_("cases")
            .delete()
            .eq("id", case_id)
            .eq("user_id", user_id)
            .execute()
        )
        logger.info("Deleted case=%s for user=%s", case_id, user_id)
    except Exception as exc:
        logger.error("DB delete failed for case=%s: %s", case_id, exc)
        raise HTTPException(
            status_code=503,
            detail={"error": "service_unavailable", "message": "Could not delete case"},
        ) from exc

    return {"deleted": True, "case_id": case_id, "filesystem": fs_results}
