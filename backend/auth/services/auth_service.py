"""
Authentication service — registration, login, logout, refresh, password reset,
and email verification.

All public methods are async. Supabase is called for identity operations;
business rules (validation, lockout) are enforced locally.

Requirements: 1.1–1.4, 2.1–2.5, 6.5
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from backend.auth.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+$")
_SPECIAL_CHARS = set(r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""")

_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15
_SESSION_MAX_DAYS = 30


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


def _is_email_exists_error(exc: Exception) -> bool:
    """Return True if the Supabase error indicates the email is already registered."""
    msg = str(exc).lower()
    return "already registered" in msg or "user already exists" in msg or "email_exists" in msg


def _is_email_not_verified_error(exc: Exception) -> bool:
    """Return True if the Supabase error indicates the email has not been verified."""
    msg = str(exc).lower()
    return "email not confirmed" in msg or "email_not_confirmed" in msg or "not verified" in msg


def _is_invalid_refresh_token_error(exc: Exception) -> bool:
    """Return True if the Supabase error indicates a bad/reused refresh token."""
    msg = str(exc).lower()
    return (
        "invalid refresh token" in msg
        or "refresh_token" in msg
        or "already used" in msg
        or "token not found" in msg
    )


def _is_expired_or_invalid_link_error(exc: Exception) -> bool:
    """Return True if the Supabase error indicates an expired or already-used reset link."""
    msg = str(exc).lower()
    return (
        "expired" in msg
        or "invalid" in msg
        or "already used" in msg
        or "token has expired" in msg
        or "otp" in msg
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def register(email: str, password: str) -> dict:
    """Create a new user account.

    Parameters
    ----------
    email:
        The prospective user's email address.
    password:
        The chosen password — must pass complexity rules.

    Returns
    -------
    dict
        ``{"user_id": str, "email": str, "message": "Verification email sent"}``

    Raises
    ------
    HTTPException 422
        Email format or password complexity failure.
    HTTPException 409
        Email is already registered.
    """
    _validate_email(email)
    _validate_password(password)

    supabase = await get_supabase_client()
    try:
        response = await supabase.auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        if _is_email_exists_error(exc):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "email_in_use",
                    "message": "An account with this email already exists",
                },
            ) from exc
        logger.error("Unexpected error during sign_up for %s: %s", email, exc)
        raise HTTPException(status_code=500, detail={"error": "internal_error"}) from exc

    # Supabase may return a user-already-exists scenario without raising — detect it
    # by checking for a null identity list on the returned user.
    user = getattr(response, "user", None)
    if user is None:
        # sign_up returned no user — treat as conflict to be safe
        raise HTTPException(
            status_code=409,
            detail={
                "error": "email_in_use",
                "message": "An account with this email already exists",
            },
        )

    # Detect "ghost" sign-up: Supabase returns a user but with no identities,
    # meaning the email was already registered.
    identities = getattr(user, "identities", None)
    if identities is not None and len(identities) == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "email_in_use",
                "message": "An account with this email already exists",
            },
        )

    return {
        "user_id": str(user.id),
        "email": email,
        "message": "Verification email sent",
    }


async def login(email: str, password: str) -> dict:
    """Authenticate a user with email and password.

    Enforces:
    - Account lockout check before attempting Supabase auth.
    - Failed-attempt counter increment on any auth failure.
    - Lockout after 5 consecutive failures (15 minutes).
    - Reset of counter on success.

    Returns
    -------
    dict
        ``{"access_token", "refresh_token", "token_type", "expires_in"}``

    Raises
    ------
    HTTPException 429
        Account is temporarily locked.
    HTTPException 401
        Invalid credentials (identical body regardless of reason — anti-enumeration).
    HTTPException 403
        Email not yet verified.
    """
    supabase = await get_supabase_client()

    # ── 1. Lockout check ────────────────────────────────────────────────────
    user_row: dict | None = None
    try:
        result = (
            await supabase.from_("users")
            .select("user_id, failed_login_attempts, locked_until")
            .eq("user_id", await _resolve_user_id_by_email(supabase, email))
            .single()
            .execute()
        )
        user_row = result.data
    except Exception:
        # User may not exist in public.users yet, or email lookup failed — continue.
        user_row = None

    if user_row and user_row.get("locked_until"):
        locked_until_str = user_row["locked_until"]
        try:
            locked_until = datetime.fromisoformat(
                locked_until_str
            )
            if locked_until > datetime.now(tz=UTC):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "account_locked",
                        "message": "Account is temporarily locked. Try again later.",
                    },
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Could not parse locked_until value '%s': %s", locked_until_str, exc)

    # ── 2. Supabase auth attempt ─────────────────────────────────────────────
    auth_error: Exception | None = None
    session = None
    try:
        response = await supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        session = getattr(response, "session", None)
        if session is None:
            raise ValueError("No session returned from Supabase")
    except Exception as exc:
        auth_error = exc

    if auth_error is not None:
        # Check for unverified email before incrementing counters
        if _is_email_not_verified_error(auth_error):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "email_not_verified",
                    "message": "Please verify your email before logging in",
                    "resend_url": "/api/auth/verify-email/resend",
                },
            )

        # Increment failed counter (best-effort; swallow errors)
        await _increment_failed_attempts(supabase, email)

        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_failed",
                "message": "Invalid email or password",
            },
        )

    # ── 3. Success — reset counters ──────────────────────────────────────────
    await _reset_failed_attempts(supabase, email)

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }


async def logout(user_id: str, refresh_token: str) -> dict:
    """Sign out the current session.

    Parameters
    ----------
    user_id:
        The authenticated user's ID (for logging/audit purposes).
    refresh_token:
        The refresh token associated with the session to revoke.

    Returns
    -------
    dict
        ``{"message": "Logged out successfully"}``
    """
    supabase = await get_supabase_client()
    try:
        await supabase.auth.sign_out()
    except Exception as exc:
        logger.warning("sign_out failed for user %s: %s", user_id, exc)
        # Swallow — best-effort logout
    return {"message": "Logged out successfully"}


async def logout_all(user_id: str) -> dict:
    """Sign out all sessions for the user (global sign-out).

    Parameters
    ----------
    user_id:
        The authenticated user's ID.

    Returns
    -------
    dict
        ``{"message": "Logged out from all devices"}``
    """
    supabase = await get_supabase_client()
    try:
        # supabase-py v2 supports scope parameter for global sign-out
        await supabase.auth.sign_out({"scope": "global"})
    except TypeError:
        # Older version or different signature — fall back to default sign_out
        try:
            await supabase.auth.sign_out()
        except Exception as exc:
            logger.warning("logout_all fallback sign_out failed for user %s: %s", user_id, exc)
    except Exception as exc:
        logger.warning("logout_all failed for user %s: %s", user_id, exc)

    return {"message": "Logged out from all devices"}


async def refresh(refresh_token: str) -> dict:
    """Exchange a refresh token for a new token pair.

    Parameters
    ----------
    refresh_token:
        The refresh token from a previous login or refresh response.

    Returns
    -------
    dict
        ``{"access_token", "refresh_token", "token_type", "expires_in"}``

    Raises
    ------
    HTTPException 401
        Token is invalid, has already been used, or the session exceeds 30 days.
    """
    supabase = await get_supabase_client()
    try:
        response = await supabase.auth.refresh_session(refresh_token)
        session = getattr(response, "session", None)
        if session is None:
            raise ValueError("No session in refresh response")
    except Exception as exc:
        if _is_invalid_refresh_token_error(exc):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_refresh_token",
                    "message": "Refresh token is invalid or has already been used",
                },
            ) from exc
        logger.error("Unexpected error during refresh_session: %s", exc)
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_refresh_token",
                "message": "Refresh token is invalid or has already been used",
            },
        ) from exc

    # ── Session age check (30-day hard limit) ────────────────────────────────
    created_at = getattr(session, "created_at", None)
    if created_at is not None:
        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            session_age = datetime.now(tz=UTC) - created_at
            if session_age > timedelta(days=_SESSION_MAX_DAYS):
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "session_expired",
                        "message": "Session has exceeded the 30-day limit. Please log in again.",
                    },
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Could not check session age: %s", exc)

    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "token_type": "bearer",
        "expires_in": 3600,
    }


async def request_password_reset(email: str) -> dict:
    """Send a password reset email.

    Always returns the same response body whether or not the email is
    registered (anti-enumeration).

    Returns
    -------
    dict
        ``{"message": "If an account with that email exists, a password reset link has been sent"}``
    """
    _anti_enum_response = {
        "message": "If an account with that email exists, a password reset link has been sent"
    }

    supabase = await get_supabase_client()
    try:
        await supabase.auth.reset_password_email(email)
    except Exception as exc:
        # Swallow all errors — never reveal whether the email exists
        logger.info("reset_password_email suppressed error for email: %s", exc)

    return _anti_enum_response


async def confirm_password_reset(token: str, new_password: str) -> dict:
    """Apply a new password using a password-reset token.

    Parameters
    ----------
    token:
        The reset token from the emailed link.
    new_password:
        The desired new password — must pass complexity rules.

    Returns
    -------
    dict
        ``{"message": "Password has been reset successfully"}``

    Raises
    ------
    HTTPException 422
        New password fails complexity rules.
    HTTPException 400
        Reset link is expired or has already been used.
    """
    _validate_password(new_password)

    supabase = await get_supabase_client()
    try:
        await supabase.auth.update_user({"password": new_password})
    except Exception as exc:
        if _is_expired_or_invalid_link_error(exc):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "link_already_used",
                    "message": "This password reset link has already been used or has expired",
                },
            ) from exc
        logger.error("Unexpected error during confirm_password_reset: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "link_already_used",
                "message": "This password reset link has already been used or has expired",
            },
        ) from exc

    return {"message": "Password has been reset successfully"}


async def resend_verification(email: str) -> dict:
    """Resend the email verification link.

    Always returns the same response body (anti-enumeration).

    Returns
    -------
    dict
        ``{"message": "If your email is registered, a verification link has been sent"}``
    """
    _anti_enum_response = {
        "message": "If your email is registered, a verification link has been sent"
    }

    supabase = await get_supabase_client()
    try:
        await supabase.auth.resend({"type": "signup", "email": email})
    except Exception as exc:
        # Swallow all errors — never reveal whether the email exists
        logger.info("resend_verification suppressed error for email: %s", exc)

    return _anti_enum_response


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


async def _resolve_user_id_by_email(supabase, email: str) -> str | None:
    """Look up the user_id in public.users for the given email via auth.users.

    Returns None if the user does not exist. Errors are swallowed so that
    lockout checks never leak user existence information.
    """
    try:
        # Use admin API to look up by email (service role key is required)
        result = await supabase.auth.admin.list_users()
        users = getattr(result, "users", result) if not isinstance(result, list) else result
        for u in users:
            if getattr(u, "email", None) == email:
                return str(u.id)
    except Exception as exc:
        logger.debug("_resolve_user_id_by_email: could not look up user: %s", exc)
    return None


async def _increment_failed_attempts(supabase, email: str) -> None:
    """Increment failed_login_attempts for the user; lock if threshold reached."""
    try:
        user_id = await _resolve_user_id_by_email(supabase, email)
        if not user_id:
            return

        # Fetch current count
        result = (
            await supabase.from_("users")
            .select("failed_login_attempts")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        row = result.data
        if row is None:
            return

        new_count = (row.get("failed_login_attempts") or 0) + 1
        update_payload: dict = {"failed_login_attempts": new_count}

        if new_count >= _MAX_FAILED_ATTEMPTS:
            locked_until = datetime.now(tz=UTC) + timedelta(minutes=_LOCKOUT_MINUTES)
            update_payload["locked_until"] = locked_until.isoformat()
            logger.info(
                "Account locked for user_id=%s after %d failed attempts",
                user_id,
                new_count,
            )

        await (
            supabase.from_("users")
            .update(update_payload)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.warning("_increment_failed_attempts: error updating user: %s", exc)


async def _reset_failed_attempts(supabase, email: str) -> None:
    """Reset failed_login_attempts and clear locked_until on successful login."""
    try:
        user_id = await _resolve_user_id_by_email(supabase, email)
        if not user_id:
            return

        await (
            supabase.from_("users")
            .update({"failed_login_attempts": 0, "locked_until": None})
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.warning("_reset_failed_attempts: error updating user: %s", exc)
