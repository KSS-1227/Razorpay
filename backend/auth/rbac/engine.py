"""
RBAC engine — FastAPI dependency factory for permission-based access control.

``require_permission(permission)`` returns a FastAPI ``Depends()``-compatible
async callable that validates the current user's role against the permission
matrix defined in ``permissions.py``.

Requirements: 5.2, 5.4
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException

from backend.auth.middleware.jwt_middleware import AuthContext, get_current_user
from backend.auth.rbac.permissions import ROLE_PERMISSIONS, Permission

# ---------------------------------------------------------------------------
# Minimum-role lookup table
# ---------------------------------------------------------------------------
# Maps each permission to the least-privileged role that holds it.
# Order of precedence (most permissive → least): Admin > Analyst > Viewer.
_PERMISSION_MIN_ROLE: dict[Permission, str] = {
    # Viewer-level permissions
    Permission.VIEW_GRAPH: "Viewer",
    Permission.READ_REPORT: "Viewer",
    # Analyst-level permissions
    Permission.UPLOAD_DOCUMENT: "Analyst",
    Permission.EXECUTE_QUERY: "Analyst",
    Permission.GENERATE_REPORT: "Analyst",
    # Admin-only permissions
    Permission.MANAGE_MEMBERS: "Admin",
    Permission.DELETE_WORKSPACE: "Admin",
    Permission.VIEW_AUDIT_LOG: "Admin",
}


def _min_role(permission: Permission) -> str:
    """Return the minimum role required to hold *permission*.

    Falls back to ``"Admin"`` for any unrecognised permission value so that
    unknown permissions are never accidentally granted to lower-privileged
    roles.
    """
    return _PERMISSION_MIN_ROLE.get(permission, "Admin")


# ---------------------------------------------------------------------------
# Dependency factory
# ---------------------------------------------------------------------------


def require_permission(permission: Permission) -> Callable:
    """FastAPI dependency factory — returns a ``Depends()``-compatible checker.

    Usage::

        @router.get(
            "/sensitive",
            dependencies=[Depends(require_permission(Permission.VIEW_AUDIT_LOG))],
        )
        async def sensitive_endpoint(auth: AuthContext = Depends(get_current_user)):
            ...

    Or as an injected dependency that also returns the ``AuthContext``::

        @router.get("/upload")
        async def upload(
            auth: AuthContext = Depends(require_permission(Permission.UPLOAD_DOCUMENT))
        ):
            ...
    """

    async def check(
        auth: AuthContext = Depends(get_current_user),
    ) -> AuthContext:
        if permission not in ROLE_PERMISSIONS.get(auth.role, set()):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_permissions",
                    "required_role": _min_role(permission),
                },
            )
        return auth

    return check
