"""
Audit routes — query the audit log for a workspace.

Mounted at /api/workspaces in main.py (alongside workspace.py); no prefix is
defined here.  The full path for the endpoint is therefore:

    GET /api/workspaces/{workspace_id}/audit-log

Requires VIEW_AUDIT_LOG permission (Admin-only).

Requirements: 10.3–10.5
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from backend.auth.middleware.jwt_middleware import AuthContext
from backend.auth.models.audit import AuditLogPage
from backend.auth.rbac.engine import require_permission
from backend.auth.rbac.permissions import Permission
from backend.auth.services import audit_service

router = APIRouter()


@router.get("/{workspace_id}/audit-log")
async def get_audit_log(
    workspace_id: str,
    cursor: str | None = None,
    limit: int | None = Query(default=200, le=200, ge=1),
    auth: AuthContext = Depends(require_permission(Permission.VIEW_AUDIT_LOG)),
) -> JSONResponse:
    """Return a cursor-paginated audit log for the given workspace.

    Only users with the VIEW_AUDIT_LOG permission (Admin role) may access this
    endpoint.

    Parameters
    ----------
    workspace_id:
        UUID of the workspace whose audit log is requested.
    cursor:
        Opaque pagination cursor returned in a previous response.  When
        omitted the first page is returned (newest entries first).
    limit:
        Maximum number of entries to return per page.  Must be in [1, 200];
        defaults to 200.

    Returns
    -------
    JSONResponse 200
        ``AuditLogPage`` serialised as JSON — ``entries`` list and optional
        ``next_cursor`` string.

    Raises
    ------
    HTTPException 403
        Requesting user lacks the VIEW_AUDIT_LOG permission.
    """
    page: AuditLogPage = await audit_service.query_audit_log(
        workspace_id=workspace_id,
        cursor=cursor,
        limit=limit,
    )
    return JSONResponse(status_code=200, content=page.model_dump(mode="json"))
