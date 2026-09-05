"""
Cases API — full CRUD for cases owned by the authenticated user.

Endpoints:
    POST   /api/cases           — create a case
    GET    /api/cases           — list all cases for the current user
    GET    /api/cases/{case_id} — get a single case
    PATCH  /api/cases/{case_id} — update title and/or description
    DELETE /api/cases/{case_id} — delete case + all associated data

Security:
    - user_id is sourced exclusively from the validated JWT (get_current_user).
    - Ownership is verified on every single-resource operation.
    - No user_id is ever read from the request body or query parameters.
    - Deleting a case removes: uploads, working, output, cache, reports,
      graphs directories AND the Supabase Storage folder.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.services import case_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/cases",
    tags=["Cases"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CaseCreateRequest(BaseModel):
    title: str
    description: str | None = None


class CaseUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
@router.post("/", status_code=201, include_in_schema=False)
async def create_case(
    body: CaseCreateRequest,
    auth: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    """Create a new case for the authenticated user.

    user_id is taken from the JWT — never from the request body.

    Returns
    -------
    JSONResponse 201
        The created case record.
    """
    result = await case_service.create_case(
        user_id=auth.user_id,       # from JWT only
        title=body.title,
        description=body.description,
    )
    return JSONResponse(status_code=201, content=result)


@router.get("")
@router.get("/", include_in_schema=False)
async def list_cases(
    auth: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    """Return all cases belonging to the authenticated user, newest first.

    Returns
    -------
    JSONResponse 200
        ``{"cases": [...]}``
    """
    cases = await case_service.list_cases(user_id=auth.user_id)
    return JSONResponse(status_code=200, content={"cases": cases})


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    auth: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    """Fetch a single case by ID.

    Ownership is verified — returns 404 if the case does not belong
    to the authenticated user.

    Returns
    -------
    JSONResponse 200
        The case record.
    """
    case = await case_service.get_case(case_id=case_id, user_id=auth.user_id)
    return JSONResponse(status_code=200, content=case)


@router.patch("/{case_id}")
async def update_case(
    case_id: str,
    body: CaseUpdateRequest,
    auth: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    """Partially update a case's title and/or description.

    Ownership is verified before any write.
    Only provided fields are updated (PATCH semantics).

    Returns
    -------
    JSONResponse 200
        The updated case record.
    """
    updated = await case_service.update_case(
        case_id=case_id,
        user_id=auth.user_id,       # from JWT only
        title=body.title,
        description=body.description,
    )
    return JSONResponse(status_code=200, content=updated)


@router.delete("/{case_id}", status_code=200)
async def delete_case(
    case_id: str,
    auth: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    """Delete a case and ALL associated data.

    Deletes in this order:
      1. Verify ownership
      2. Local filesystem: uploads/, working/, output/, cache/, reports/, graphs/
      3. Supabase Storage: users/{user_id}/{case_id}/
      4. Database row in public.cases

    Returns
    -------
    JSONResponse 200
        ``{"deleted": true, "case_id": "...", "filesystem": {...}}``

    Raises
    ------
    HTTPException 404
        Case not found or does not belong to the current user.
    """
    result = await case_service.delete_case(
        case_id=case_id,
        user_id=auth.user_id,       # from JWT only
    )
    return JSONResponse(status_code=200, content=result)
