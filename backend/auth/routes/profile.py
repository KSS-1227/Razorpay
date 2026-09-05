"""
Profile routes — GET and PATCH /profile/{user_id}.

Mounted at /api/auth in main.py, so the full paths are:
  GET  /api/auth/profile/{user_id}
  PATCH /api/auth/profile/{user_id}

Both endpoints require a valid JWT. Users may only access or modify their own
profile — the user_id path parameter is compared against the authenticated
user's sub claim, and HTTP 403 is returned if they differ.

Requirements: 7.1–7.3
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.middleware.jwt_middleware import AuthContext, get_current_user
from backend.auth.models.user import ProfileUpdateRequest, UserProfile
from backend.auth.services import profile_service

router = APIRouter(tags=["profile"])


def _assert_own_profile(user_id: str, current_user: AuthContext) -> None:
    """Raise HTTP 403 if *user_id* does not match the authenticated user's ID."""
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "You can only access your own profile",
            },
        )


@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_profile(
    user_id: str,
    current_user: AuthContext = Depends(get_current_user),
) -> UserProfile:
    """Retrieve the profile for *user_id*.

    The authenticated user may only fetch their own profile.

    Responses
    ---------
    200 : UserProfile JSON
    403 : user_id does not match the authenticated user
    404 : user not found (forwarded from profile_service)
    """
    _assert_own_profile(user_id, current_user)
    return await profile_service.get_profile(user_id)


@router.patch("/profile/{user_id}", response_model=UserProfile)
async def update_profile(
    user_id: str,
    update: ProfileUpdateRequest,
    current_user: AuthContext = Depends(get_current_user),
) -> UserProfile:
    """Partially update the profile for *user_id*.

    All fields in the request body are optional; only supplied (non-None)
    fields are written to the database.

    The authenticated user may only update their own profile.

    Responses
    ---------
    200 : updated UserProfile JSON
    403 : user_id does not match the authenticated user
    404 : user not found (forwarded from profile_service)
    422 : validation errors (forwarded from profile_service)
    """
    _assert_own_profile(user_id, current_user)
    return await profile_service.update_profile(user_id, update)
