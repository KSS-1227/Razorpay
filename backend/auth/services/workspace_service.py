"""
Workspace service — create, list, delete workspaces, and manage members.

All public methods are async. Supabase service role client is used for all
DB operations (bypasses RLS). Admin API is used for auth.users access.

Requirements: 3.1–3.6, 4.1–4.5, 5.1–5.4
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException

from backend.auth.rbac.permissions import ROLE_PERMISSIONS, Permission
from backend.auth.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKSPACE_NAME_MIN = 3
_WORKSPACE_NAME_MAX = 80
_MAX_MEMBERS = 50
_INVITE_EXPIRY_HOURS = 72


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _log_audit_event(
    event_type: str,
    user_id: str | None,
    workspace_id: str | None,
    source_ip: str = "system",
    detail: str = "",
) -> None:
    """Insert an audit log entry. Errors are swallowed — never block caller."""
    try:
        supabase = await get_supabase_client()
        await supabase.from_("audit_log").insert(
            {
                "entry_id": str(uuid4()),
                "event_type": event_type,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "source_ip": source_ip,
                "detail": detail[:2000],
            }
        ).execute()
    except Exception as exc:
        logger.error("Audit log insert failed: %s", exc)


async def _get_member_role(supabase, workspace_id: str, user_id: str) -> str | None:
    """Return the active role for user_id in workspace_id, or None if not a member."""
    try:
        result = (
            await supabase.from_("workspace_members")
            .select("role")
            .eq("workspace_id", workspace_id)
            .eq("user_id", user_id)
            .eq("membership_status", "active")
            .single()
            .execute()
        )
        return result.data["role"] if result.data else None
    except Exception:
        return None


def _has_permission(role: str | None, permission: Permission) -> bool:
    """Return True if the given role includes the specified permission."""
    if role is None:
        return False
    return permission in ROLE_PERMISSIONS.get(role, set())


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def create_workspace(owner_id: str, name: str) -> dict:
    """Create a new workspace and add the owner as Admin.

    Parameters
    ----------
    owner_id:
        The UUID of the user who will own the workspace.
    name:
        The desired workspace name (3–80 characters).

    Returns
    -------
    dict
        WorkspaceResponse with workspace_id, name, created_at, member_count=1, role="Admin".

    Raises
    ------
    HTTPException 422
        Name is outside the 3–80 character range.
    HTTPException 409
        A workspace with this name already exists for the owner.
    """
    # ── 1. Validate name ─────────────────────────────────────────────────────
    if not (_WORKSPACE_NAME_MIN <= len(name) <= _WORKSPACE_NAME_MAX):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": (
                    f"Workspace name must be between {_WORKSPACE_NAME_MIN} "
                    f"and {_WORKSPACE_NAME_MAX} characters"
                ),
            },
        )

    supabase = await get_supabase_client()
    workspace_id = str(uuid4())
    now = datetime.now(tz=UTC)

    # ── 2. Insert workspace ───────────────────────────────────────────────────
    try:
        await supabase.from_("workspaces").insert(
            {
                "workspace_id": workspace_id,
                "name": name,
                "owner_id": owner_id,
                "is_deleted": False,
                "created_at": now.isoformat(),
            }
        ).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "workspace_name_taken",
                    "message": "A workspace with this name already exists",
                },
            ) from exc
        logger.error("Error creating workspace for owner_id=%s: %s", owner_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to create workspace"},
        ) from exc

    # ── 3. Add owner as Admin member ─────────────────────────────────────────
    try:
        await supabase.from_("workspace_members").insert(
            {
                "member_id": str(uuid4()),
                "user_id": owner_id,
                "workspace_id": workspace_id,
                "role": "Admin",
                "membership_status": "active",
                "invited_at": now.isoformat(),
                "activated_at": now.isoformat(),
                "expires_at": None,
            }
        ).execute()
    except Exception as exc:
        logger.error(
            "Error adding owner as admin member for workspace_id=%s: %s", workspace_id, exc
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "Failed to initialise workspace membership",
            },
        ) from exc

    # ── 4. Audit log ─────────────────────────────────────────────────────────
    await _log_audit_event(
        event_type="workspace_created",
        user_id=owner_id,
        workspace_id=workspace_id,
        detail=f"Workspace '{name}' created",
    )

    return {
        "workspace_id": workspace_id,
        "name": name,
        "created_at": now.isoformat(),
        "member_count": 1,
        "role": "Admin",
    }


async def list_workspaces(user_id: str) -> list[dict]:
    """Return all active workspaces the user is an active member of.

    Parameters
    ----------
    user_id:
        The UUID of the requesting user.

    Returns
    -------
    list[dict]
        List of WorkspaceResponse dicts including member_count and the
        requesting user's role.
    """
    supabase = await get_supabase_client()

    # Fetch workspace memberships for this user
    try:
        memberships_result = (
            await supabase.from_("workspace_members")
            .select("workspace_id, role")
            .eq("user_id", user_id)
            .eq("membership_status", "active")
            .execute()
        )
    except Exception as exc:
        logger.error("Error fetching workspace memberships for user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to list workspaces"},
        ) from exc

    memberships = memberships_result.data or []
    if not memberships:
        return []

    workspace_ids = [m["workspace_id"] for m in memberships]
    role_by_workspace = {m["workspace_id"]: m["role"] for m in memberships}

    # Fetch workspace records (non-deleted)
    try:
        workspaces_result = (
            await supabase.from_("workspaces")
            .select("workspace_id, name, created_at")
            .in_("workspace_id", workspace_ids)
            .eq("is_deleted", False)
            .execute()
        )
    except Exception as exc:
        logger.error("Error fetching workspaces for user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to list workspaces"},
        ) from exc

    workspaces = workspaces_result.data or []

    # Build member count map: count active members per workspace
    try:
        counts_result = (
            await supabase.from_("workspace_members")
            .select("workspace_id")
            .in_("workspace_id", workspace_ids)
            .eq("membership_status", "active")
            .execute()
        )
        counts_data = counts_result.data or []
    except Exception as exc:
        logger.warning("Error fetching member counts: %s", exc)
        counts_data = []

    member_count_map: dict[str, int] = {}
    for row in counts_data:
        wid = row["workspace_id"]
        member_count_map[wid] = member_count_map.get(wid, 0) + 1

    result: list[dict] = []
    for ws in workspaces:
        wid = ws["workspace_id"]
        result.append(
            {
                "workspace_id": wid,
                "name": ws["name"],
                "created_at": ws["created_at"],
                "member_count": member_count_map.get(wid, 0),
                "role": role_by_workspace.get(wid, "Viewer"),
            }
        )

    return result


async def delete_workspace(workspace_id: str, requesting_user_id: str) -> dict:
    """Soft-delete a workspace (Admin only).

    Parameters
    ----------
    workspace_id:
        The UUID of the workspace to delete.
    requesting_user_id:
        The UUID of the user requesting the deletion.

    Returns
    -------
    dict
        ``{"message": "Workspace deleted successfully"}``

    Raises
    ------
    HTTPException 403
        Requesting user does not have DELETE_WORKSPACE permission.
    HTTPException 404
        Workspace does not exist or is already deleted.
    """
    supabase = await get_supabase_client()

    # ── 1. Permission check ───────────────────────────────────────────────────
    role = await _get_member_role(supabase, workspace_id, requesting_user_id)
    if not _has_permission(role, Permission.DELETE_WORKSPACE):
        raise HTTPException(
            status_code=403,
            detail={"error": "insufficient_permissions"},
        )

    # ── 2. Verify workspace exists and is not already deleted ─────────────────
    try:
        ws_result = (
            await supabase.from_("workspaces")
            .select("workspace_id, name")
            .eq("workspace_id", workspace_id)
            .eq("is_deleted", False)
            .single()
            .execute()
        )
        ws_row = ws_result.data
    except Exception:
        ws_row = None

    if not ws_row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found"},
        )

    # ── 3. Soft-delete ────────────────────────────────────────────────────────
    now = datetime.now(tz=UTC)
    try:
        await supabase.from_("workspaces").update(
            {
                "is_deleted": True,
                "deleted_at": now.isoformat(),
            }
        ).eq("workspace_id", workspace_id).execute()
    except Exception as exc:
        logger.error("Error soft-deleting workspace_id=%s: %s", workspace_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to delete workspace"},
        ) from exc

    # ── 4. Audit log ─────────────────────────────────────────────────────────
    await _log_audit_event(
        event_type="workspace_deleted",
        user_id=requesting_user_id,
        workspace_id=workspace_id,
        detail=f"Workspace '{ws_row.get('name', workspace_id)}' deleted",
    )

    return {"message": "Workspace deleted successfully"}


async def invite_member(
    workspace_id: str,
    email: str,
    role: str,
    inviting_user_id: str,
) -> dict:
    """Invite a user to a workspace by email.

    Parameters
    ----------
    workspace_id:
        The UUID of the target workspace.
    email:
        Email address of the user to invite.
    role:
        The role to assign (Admin, Analyst, or Viewer).
    inviting_user_id:
        The UUID of the user sending the invitation.

    Returns
    -------
    dict
        ``{"message": "Invitation sent", "member_id": str}``

    Raises
    ------
    HTTPException 422
        Workspace has already reached the 50-member cap.
    HTTPException 403
        Inviting user does not have MANAGE_MEMBERS permission.
    HTTPException 404
        Invitee email not found in auth users.
    """
    supabase = await get_supabase_client()

    # ── 1. Permission check ───────────────────────────────────────────────────
    inviter_role = await _get_member_role(supabase, workspace_id, inviting_user_id)
    if not _has_permission(inviter_role, Permission.MANAGE_MEMBERS):
        raise HTTPException(
            status_code=403,
            detail={"error": "insufficient_permissions"},
        )

    # ── 2. Member cap check ───────────────────────────────────────────────────
    try:
        count_result = (
            await supabase.from_("workspace_members")
            .select("member_id")
            .eq("workspace_id", workspace_id)
            .eq("membership_status", "active")
            .execute()
        )
        active_count = len(count_result.data or [])
    except Exception as exc:
        logger.error("Error counting members for workspace_id=%s: %s", workspace_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to check member count"},
        ) from exc

    if active_count >= _MAX_MEMBERS:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "member_cap_reached",
                "message": "Workspace cannot exceed 50 members",
            },
        )

    # ── 3. Look up invitee by email via admin API ─────────────────────────────
    invitee_user_id: str | None = None
    try:
        result = await supabase.auth.admin.list_users()
        users = getattr(result, "users", result) if not isinstance(result, list) else result
        for u in users:
            if getattr(u, "email", None) == email:
                invitee_user_id = str(u.id)
                break
    except Exception as exc:
        logger.error("Error looking up user by email: %s", exc)

    if not invitee_user_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "user_not_found"},
        )

    # ── 4. Insert pending membership ──────────────────────────────────────────
    now = datetime.now(tz=UTC)
    member_id = str(uuid4())
    expires_at = (now + timedelta(hours=_INVITE_EXPIRY_HOURS)).isoformat()

    try:
        await supabase.from_("workspace_members").insert(
            {
                "member_id": member_id,
                "workspace_id": workspace_id,
                "user_id": invitee_user_id,
                "role": role,
                "membership_status": "pending",
                "invited_at": now.isoformat(),
                "activated_at": None,
                "expires_at": expires_at,
            }
        ).execute()
    except Exception as exc:
        logger.error(
            "Error inserting workspace member for workspace_id=%s email=%s: %s",
            workspace_id,
            email,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to create invitation"},
        ) from exc

    # ── 5. Best-effort invitation email ──────────────────────────────────────
    try:
        await supabase.auth.admin.invite_user_by_email(email)
    except Exception as exc:
        logger.warning("Could not send invitation email to %s: %s", email, exc)

    # ── 6. Audit log ─────────────────────────────────────────────────────────
    await _log_audit_event(
        event_type="workspace_member_added",
        user_id=inviting_user_id,
        workspace_id=workspace_id,
        detail=f"Invited {email} with role {role}",
    )

    return {"message": "Invitation sent", "member_id": member_id}


async def remove_member(
    workspace_id: str,
    target_user_id: str,
    requesting_user_id: str,
) -> dict:
    """Remove a member from a workspace (Admin only).

    Parameters
    ----------
    workspace_id:
        The UUID of the workspace.
    target_user_id:
        The UUID of the user to remove.
    requesting_user_id:
        The UUID of the user performing the action.

    Returns
    -------
    dict
        ``{"message": "Member removed successfully"}``

    Raises
    ------
    HTTPException 403
        Requesting user does not have MANAGE_MEMBERS permission.
    HTTPException 404
        Target member record not found or already removed.
    """
    supabase = await get_supabase_client()

    # ── 1. Permission check ───────────────────────────────────────────────────
    requester_role = await _get_member_role(supabase, workspace_id, requesting_user_id)
    if not _has_permission(requester_role, Permission.MANAGE_MEMBERS):
        raise HTTPException(
            status_code=403,
            detail={"error": "insufficient_permissions"},
        )

    # ── 2. Verify target member exists ────────────────────────────────────────
    try:
        target_result = (
            await supabase.from_("workspace_members")
            .select("member_id")
            .eq("workspace_id", workspace_id)
            .eq("user_id", target_user_id)
            .eq("membership_status", "active")
            .single()
            .execute()
        )
        target_row = target_result.data
    except Exception:
        target_row = None

    if not target_row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found"},
        )

    # ── 3. Mark as removed ───────────────────────────────────────────────────
    try:
        await supabase.from_("workspace_members").update(
            {"membership_status": "removed"}
        ).eq("workspace_id", workspace_id).eq("user_id", target_user_id).execute()
    except Exception as exc:
        logger.error(
            "Error removing member user_id=%s from workspace_id=%s: %s",
            target_user_id,
            workspace_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to remove member"},
        ) from exc

    # ── 4. Best-effort session revocation ─────────────────────────────────────
    try:
        await supabase.auth.admin.sign_out(target_user_id)
    except Exception as exc:
        logger.warning(
            "Could not revoke sessions for user_id=%s: %s", target_user_id, exc
        )

    # ── 5. Audit log ─────────────────────────────────────────────────────────
    await _log_audit_event(
        event_type="workspace_member_removed",
        user_id=requesting_user_id,
        workspace_id=workspace_id,
        detail=f"Removed member user_id={target_user_id}",
    )

    return {"message": "Member removed successfully"}


async def change_member_role(
    workspace_id: str,
    target_user_id: str,
    new_role: str,
    requesting_user_id: str,
) -> dict:
    """Change a workspace member's role (Admin only).

    Parameters
    ----------
    workspace_id:
        The UUID of the workspace.
    target_user_id:
        The UUID of the member whose role to change.
    new_role:
        The new role to assign (Admin, Analyst, or Viewer).
    requesting_user_id:
        The UUID of the user performing the action.

    Returns
    -------
    dict
        ``{"message": "Role updated successfully", "new_role": new_role}``

    Raises
    ------
    HTTPException 403
        Requesting user does not have MANAGE_MEMBERS permission.
    HTTPException 409
        Attempting to demote the sole remaining Admin.
    """
    supabase = await get_supabase_client()

    # ── 1. Permission check ───────────────────────────────────────────────────
    requester_role = await _get_member_role(supabase, workspace_id, requesting_user_id)
    if not _has_permission(requester_role, Permission.MANAGE_MEMBERS):
        raise HTTPException(
            status_code=403,
            detail={"error": "insufficient_permissions"},
        )

    # ── 2. Sole-admin guard (only applies when changing own role away from Admin) ──
    if target_user_id == requesting_user_id and new_role != "Admin":
        try:
            admins_result = (
                await supabase.from_("workspace_members")
                .select("user_id")
                .eq("workspace_id", workspace_id)
                .eq("role", "Admin")
                .eq("membership_status", "active")
                .execute()
            )
            admin_count = len(admins_result.data or [])
        except Exception as exc:
            logger.warning("Error counting admins for workspace_id=%s: %s", workspace_id, exc)
            admin_count = 0

        if admin_count <= 1:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "sole_admin",
                    "message": "Cannot remove yourself as the sole admin",
                },
            )

    # ── 3. Apply role change ──────────────────────────────────────────────────
    try:
        result = (
            await supabase.from_("workspace_members")
            .update({"role": new_role})
            .eq("workspace_id", workspace_id)
            .eq("user_id", target_user_id)
            .eq("membership_status", "active")
            .execute()
        )
        updated = result.data or []
    except Exception as exc:
        logger.error(
            "Error changing role for user_id=%s in workspace_id=%s: %s",
            target_user_id,
            workspace_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to update role"},
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found"},
        )

    # ── 4. Audit log (best-effort — must not block role change) ───────────────
    await _log_audit_event(
        event_type="role_changed",
        user_id=requesting_user_id,
        workspace_id=workspace_id,
        detail=f"Changed role of user_id={target_user_id} to {new_role}",
    )

    return {"message": "Role updated successfully", "new_role": new_role}
