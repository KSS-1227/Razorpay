"""
Workspace routes — list, create, delete workspaces and manage members.

Mounted at /api/workspaces.

All endpoints require a valid JWT.
Permission-protected endpoints additionally require RBAC permissions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.auth.middleware.jwt_middleware import (
    AuthContext,
    get_current_user,
)
from backend.auth.models.workspace import (
    MemberInviteRequest,
    MemberRoleChangeRequest,
    WorkspaceCreateRequest,
    WorkspaceResponse,
)
from backend.auth.rbac.engine import require_permission
from backend.auth.rbac.permissions import Permission
from backend.auth.services import workspace_service

router = APIRouter(
    tags=["Workspaces"],
)


# ============================================================================
# Workspace
# ============================================================================

@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    auth: AuthContext = Depends(get_current_user),
):
    workspaces = await workspace_service.list_workspaces(auth.user_id)
    return workspaces


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=201,
)
async def create_workspace(
    body: WorkspaceCreateRequest,
    auth: AuthContext = Depends(get_current_user),
):
    return await workspace_service.create_workspace(
        auth.user_id,
        body.name,
    )


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    auth: AuthContext = Depends(
        require_permission(
            Permission.DELETE_WORKSPACE
        )
    ),
):
    result = await workspace_service.delete_workspace(
        workspace_id,
        auth.user_id,
    )

    return JSONResponse(
        status_code=200,
        content=result,
    )


# ============================================================================
# Members
# ============================================================================

@router.post("/{workspace_id}/members")
async def invite_member(
    workspace_id: str,
    body: MemberInviteRequest,
    auth: AuthContext = Depends(
        require_permission(
            Permission.MANAGE_MEMBERS
        )
    ),
):
    result = await workspace_service.invite_member(
        workspace_id=workspace_id,
        email=body.email,
        role=body.role,
        requester_id=auth.user_id,
    )

    return JSONResponse(
        status_code=201,
        content=result,
    )


@router.delete("/{workspace_id}/members/{user_id}")
async def remove_member(
    workspace_id: str,
    user_id: str,
    auth: AuthContext = Depends(
        require_permission(
            Permission.MANAGE_MEMBERS
        )
    ),
):
    result = await workspace_service.remove_member(
        workspace_id,
        user_id,
        auth.user_id,
    )

    return JSONResponse(
        status_code=200,
        content=result,
    )


@router.patch("/{workspace_id}/members/{user_id}/role")
async def change_member_role(
    workspace_id: str,
    user_id: str,
    body: MemberRoleChangeRequest,
    auth: AuthContext = Depends(
        require_permission(
            Permission.MANAGE_MEMBERS
        )
    ),
):
    result = await workspace_service.change_member_role(
        workspace_id,
        user_id,
        body.role,
        auth.user_id,
    )

    return JSONResponse(
        status_code=200,
        content=result,
    )
