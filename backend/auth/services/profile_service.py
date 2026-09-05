"""
Profile service — get profile, update profile, change email, change password.

All public methods are async. Supabase service role client is used for all
DB operations (bypasses RLS). Admin API is used for auth.users access.

Requirements: 7.1–7.6
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from fastapi import HTTPException

from backend.auth.models.user import ProfileUpdateRequest, UserProfile
from backend.auth.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+$")
_SPECIAL_CHARS = set(r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""")
_BCP47_PATTERN = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_email(email: str) -> None:
    """Raise HTTP 422 if *email* does not have non-empty local@domain shape."""
    if not email or not _EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(
            status_code=422,
            detail={"error": "validation_error", "message": "Invalid email format"},
        )
    local, domain = email.split("@", 1)
    if not local or not domain:
        raise HTTPException(
            status_code=422,
            detail={"error": "validation_error", "message": "Invalid email format"},
        )


def _validate_password(password: str) -> None:
    """Raise HTTP 422 with a violations list if *password* fails complexity rules.

    Rules:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    violations: list[str] = []

    if len(password) < 8:
        violations.append("too_short")
    if not any(c.isupper() for c in password):
        violations.append("missing_uppercase")
    if not any(c.islower() for c in password):
        violations.append("missing_lowercase")
    if not any(c.isdigit() for c in password):
        violations.append("missing_digit")
    if not any(c in _SPECIAL_CHARS for c in password):
        violations.append("missing_special_character")

    if violations:
        raise HTTPException(
            status_code=422,
            detail={"error": "password_complexity", "violations": violations},
        )


def _validate_display_name(value: str) -> None:
    """Raise HTTP 422 if display_name is outside 1–100 characters."""
    if not (1 <= len(value) <= 100):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": "display_name must be between 1 and 100 characters",
            },
        )


def _validate_avatar_url(value: str) -> None:
    """Raise HTTP 422 if avatar_url does not use HTTPS scheme."""
    if not value.startswith("https://"):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": "avatar_url must use the HTTPS scheme",
            },
        )


def _validate_preferred_language(value: str) -> None:
    """Raise HTTP 422 if preferred_language is not a valid BCP 47 tag."""
    if not _BCP47_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": (
                    "preferred_language must be a valid BCP 47 language tag "
                    "(e.g. 'en', 'en-US', 'zh-Hans')"
                ),
            },
        )


async def _fetch_public_user(supabase, user_id: str) -> dict:
    """Fetch a row from public.users by user_id.

    Raises HTTP 404 if not found.
    """
    try:
        result = (
            await supabase.from_("users")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        row = result.data
    except Exception as exc:
        logger.warning("Error fetching public.users for user_id=%s: %s", user_id, exc)
        row = None

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "User not found"},
        )
    return row


async def _fetch_auth_user(supabase, user_id: str) -> tuple[str, bool]:
    """Fetch email and email_verified from auth.users via the admin API.

    Returns
    -------
    tuple[str, bool]
        ``(email, email_verified)``

    Raises HTTP 404 if the auth user is not found.
    """
    try:
        auth_response = await supabase.auth.admin.get_user_by_id(user_id)
        user_obj = getattr(auth_response, "user", auth_response)
        email = getattr(user_obj, "email", None)
        email_confirmed_at = getattr(user_obj, "email_confirmed_at", None)
    except Exception as exc:
        logger.warning("Error fetching auth.users for user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "User not found"},
        ) from exc

    if not email:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "User not found"},
        )

    email_verified = email_confirmed_at is not None
    return email, email_verified


def _build_user_profile(row: dict, email: str, email_verified: bool) -> UserProfile:
    """Construct a UserProfile from a public.users row and auth.users data."""
    return UserProfile(
        user_id=str(row["user_id"]),
        email=email,
        display_name=row["display_name"],
        avatar_url=row.get("avatar_url"),
        preferred_language=row["preferred_language"],
        preferred_date_format=row["preferred_date_format"],
        email_verified=email_verified,
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def get_profile(user_id: str) -> UserProfile:
    """Fetch the full profile for a given user.

    Parameters
    ----------
    user_id:
        The UUID of the user whose profile is requested.

    Returns
    -------
    UserProfile
        Populated profile model combining public.users and auth.users data.

    Raises
    ------
    HTTPException 404
        User not found in public.users or auth.users.
    """
    supabase = await get_supabase_client()

    row = await _fetch_public_user(supabase, user_id)
    email, email_verified = await _fetch_auth_user(supabase, user_id)

    return _build_user_profile(row, email, email_verified)


async def update_profile(user_id: str, update: ProfileUpdateRequest) -> UserProfile:
    """Partially update a user's profile.

    Only fields that are not ``None`` in *update* are written to the database.
    Validation is re-enforced here (display_name length, avatar_url HTTPS,
    preferred_language BCP 47) even though Pydantic validators on the model
    already run at request-parse time — this ensures service-layer correctness
    if called programmatically.

    Parameters
    ----------
    user_id:
        The UUID of the user to update.
    update:
        Partial update payload.

    Returns
    -------
    UserProfile
        The updated profile.

    Raises
    ------
    HTTPException 404
        User not found.
    HTTPException 422
        Validation failure on any supplied field.
    """
    # ── 1. Validate supplied fields ──────────────────────────────────────────
    if update.display_name is not None:
        _validate_display_name(update.display_name)

    if update.avatar_url is not None:
        # avatar_url is already an HttpUrl from Pydantic; convert to str for check
        _validate_avatar_url(str(update.avatar_url))

    if update.preferred_language is not None:
        _validate_preferred_language(update.preferred_language)

    # ── 2. Build update payload from non-None fields ─────────────────────────
    payload: dict = {}
    if update.display_name is not None:
        payload["display_name"] = update.display_name
    if update.avatar_url is not None:
        payload["avatar_url"] = str(update.avatar_url)
    if update.preferred_language is not None:
        payload["preferred_language"] = update.preferred_language
    if update.preferred_date_format is not None:
        payload["preferred_date_format"] = update.preferred_date_format

    if not payload:
        # Nothing to update — return current profile unchanged
        return await get_profile(user_id)

    payload["updated_at"] = datetime.now(tz=UTC).isoformat()

    # ── 3. Verify user exists before attempting update ────────────────────────
    supabase = await get_supabase_client()
    await _fetch_public_user(supabase, user_id)  # raises 404 if not found

    # ── 4. Persist update ────────────────────────────────────────────────────
    try:
        result = (
            await supabase.from_("users")
            .update(payload)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.error("Error updating public.users for user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to update profile"},
        ) from exc

    updated_rows = result.data
    if not updated_rows:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "User not found"},
        )

    # ── 5. Fetch and return updated profile ───────────────────────────────────
    return await get_profile(user_id)


async def change_email(user_id: str, new_email: str) -> dict:
    """Initiate an email-change flow.

    Validates *new_email* format, then calls the Supabase admin API to update
    the user's email. Supabase will send a verification email to the new
    address; the change is not committed until the user confirms it.

    Parameters
    ----------
    user_id:
        The UUID of the authenticated user requesting the change.
    new_email:
        The desired new email address.

    Returns
    -------
    dict
        ``{"message": "Verification email sent to new address"}``

    Raises
    ------
    HTTPException 422
        Invalid email format.
    HTTPException 409
        New email is already in use by another account.
    """
    _validate_email(new_email)

    supabase = await get_supabase_client()
    try:
        await supabase.auth.admin.update_user_by_id(
            user_id,
            {"email": new_email},
        )
    except Exception as exc:
        msg = str(exc).lower()
        if (
            "already registered" in msg
            or "user already exists" in msg
            or "email_exists" in msg
            or "already in use" in msg
            or "duplicate" in msg
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "email_in_use",
                    "message": "This email address is already in use",
                },
            ) from exc
        logger.error("Error changing email for user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to initiate email change"},
        ) from exc

    return {"message": "Verification email sent to new address"}


async def change_password(
    user_id: str,
    current_password: str,
    new_password: str,
) -> dict:
    """Change a user's password after re-authenticating with the current one.

    Steps:
    1. Fetch the user's current email from auth.users.
    2. Re-authenticate using ``sign_in_with_password`` to verify *current_password*.
    3. Validate *new_password* complexity.
    4. Update the password via the admin API.
    5. Perform a global sign-out to invalidate all existing refresh tokens.

    Parameters
    ----------
    user_id:
        The UUID of the authenticated user.
    current_password:
        The user's existing password (used for re-authentication).
    new_password:
        The desired new password — must pass complexity rules.

    Returns
    -------
    dict
        ``{"message": "Password updated successfully"}``

    Raises
    ------
    HTTPException 401
        Current password is incorrect.
    HTTPException 422
        New password fails complexity rules.
    """
    supabase = await get_supabase_client()

    # ── 1. Fetch current email ───────────────────────────────────────────────
    email, _ = await _fetch_auth_user(supabase, user_id)

    # ── 2. Re-authenticate ───────────────────────────────────────────────────
    try:
        response = await supabase.auth.sign_in_with_password(
            {"email": email, "password": current_password}
        )
        session = getattr(response, "session", None)
        if session is None:
            raise ValueError("No session returned — invalid credentials")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(
            "Re-authentication failed for user_id=%s: %s", user_id, exc
        )
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_password",
                "message": "Current password is incorrect",
            },
        ) from exc

    # ── 3. Validate new password complexity ──────────────────────────────────
    _validate_password(new_password)

    # ── 4. Update password via admin API ─────────────────────────────────────
    try:
        await supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": new_password},
        )
    except Exception as exc:
        logger.error("Error updating password for user_id=%s: %s", user_id, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": "Failed to update password"},
        ) from exc

    # ── 5. Global sign-out — invalidate all refresh tokens ───────────────────
    try:
        await supabase.auth.sign_out({"scope": "global"})
    except TypeError:
        try:
            await supabase.auth.sign_out()
        except Exception as exc:
            logger.warning(
                "Global sign-out (fallback) failed for user_id=%s: %s", user_id, exc
            )
    except Exception as exc:
        logger.warning("Global sign-out failed for user_id=%s: %s", user_id, exc)

    return {"message": "Password updated successfully"}
