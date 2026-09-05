"""
FastAPI dependency functions for auth-aware request handling.

Provides:
- get_current_user()  — validates JWT, returns AuthContext with user_id, role, workspace_id
- get_current_case()  — validates that the case_id path param belongs to the current user

Rule: user_id is ALWAYS sourced from the validated JWT (AuthContext.user_id).
      It is NEVER read from request body, query params, or any frontend-supplied value.

Requirements: 9.1–9.5
"""
from __future__ import annotations

import logging

from fastapi import Depends, Path

from backend.auth.middleware.jwt_middleware import AuthContext, get_current_user

logger = logging.getLogger(__name__)

# Re-export get_current_user so callers only need to import from this module
__all__ = ["get_current_case", "get_current_user"]


async def get_current_case(
    case_id: str = Path(..., description="UUID of the case"),
    auth: AuthContext = Depends(get_current_user),
) -> dict:
    """Validate that `case_id` exists and belongs to the authenticated user.

    Delegates to case_service.get_case() which enforces ownership via the
    JWT user_id. Returns the case row dict on success.

    Raises
    ------
    HTTPException 404
        Case not found or does not belong to the current user.
    """
    # Import here to avoid circular imports (case_service imports supabase_client,
    # not auth.dependencies)
    from backend.auth.services.case_service import get_case
    return await get_case(case_id=case_id, user_id=auth.user_id)
