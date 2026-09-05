"""
Auth routes — registration, login, logout, token refresh, password reset,
and email verification resend.

The router is mounted at /api/auth in main.py; no prefix is defined here.

All request/response shapes match design.md exactly.

Requirements: 1.1–1.5, 2.1–2.4, 4.5–4.8, 6.1–6.3
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.auth.middleware.jwt_middleware import AuthContext, get_current_user
from backend.auth.services import auth_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LogoutRequest(BaseModel):
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequestBody(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class ResendVerificationRequest(BaseModel):
    email: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/register")
async def register(body: RegisterRequest) -> JSONResponse:
    """Create a new user account and send a verification email.

    Returns
    -------
    JSONResponse 201
        ``{"user_id": str, "email": str, "message": "Verification email sent"}``

    Raises
    ------
    HTTPException 409
        Email is already in use.
    HTTPException 422
        Password complexity or email format failure.
    """
    result = await auth_service.register(body.email, body.password)
    return JSONResponse(status_code=201, content=result)


@router.post("/login")
async def login(body: LoginRequest) -> JSONResponse:
    """Authenticate with email and password.

    Returns
    -------
    JSONResponse 200
        ``{"access_token", "refresh_token", "token_type", "expires_in"}``

    Raises
    ------
    HTTPException 401
        Invalid credentials (identical response for wrong password and unknown email).
    HTTPException 403
        Email has not been verified.
    HTTPException 429
        Account is temporarily locked.
    """
    result = await auth_service.login(body.email, body.password)
    return JSONResponse(status_code=200, content=result)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    current_user: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    """Revoke the current session's refresh token.

    Requires a valid Bearer JWT in the Authorization header.

    Returns
    -------
    JSONResponse 200
        ``{"message": "Logged out successfully"}``
    """
    result = await auth_service.logout(current_user.user_id, body.refresh_token)
    return JSONResponse(status_code=200, content=result)


@router.post("/logout-all")
async def logout_all(
    current_user: AuthContext = Depends(get_current_user),
) -> JSONResponse:
    """Revoke all sessions for the authenticated user (global sign-out).

    Requires a valid Bearer JWT in the Authorization header.

    Returns
    -------
    JSONResponse 200
        ``{"message": "Logged out from all devices"}``
    """
    result = await auth_service.logout_all(current_user.user_id)
    return JSONResponse(status_code=200, content=result)


@router.post("/refresh")
async def refresh(body: RefreshRequest) -> JSONResponse:
    """Exchange a refresh token for a new access/refresh token pair.

    No JWT required — the refresh token is provided in the request body.

    Returns
    -------
    JSONResponse 200
        ``{"access_token", "refresh_token", "token_type", "expires_in"}``

    Raises
    ------
    HTTPException 401
        Refresh token is invalid, already used, or the session exceeds 30 days.
    """
    result = await auth_service.refresh(body.refresh_token)
    return JSONResponse(status_code=200, content=result)


@router.post("/password-reset/request")
async def password_reset_request(body: PasswordResetRequestBody) -> JSONResponse:
    """Send a password reset email.

    Always returns 200 regardless of whether the email is registered
    (anti-enumeration).

    Returns
    -------
    JSONResponse 200
        ``{"message": "If an account with that email exists, a password reset link has been sent"}``
    """
    result = await auth_service.request_password_reset(body.email)
    return JSONResponse(status_code=200, content=result)


@router.post("/password-reset/confirm")
async def password_reset_confirm(body: PasswordResetConfirmRequest) -> JSONResponse:
    """Apply a new password using the token from the reset email.

    Returns
    -------
    JSONResponse 200
        ``{"message": "Password has been reset successfully"}``

    Raises
    ------
    HTTPException 400
        Reset link is expired or has already been used.
    HTTPException 422
        New password fails complexity rules.
    """
    result = await auth_service.confirm_password_reset(body.token, body.new_password)
    return JSONResponse(status_code=200, content=result)


@router.post("/verify-email/resend")
async def resend_verification(body: ResendVerificationRequest) -> JSONResponse:
    """Resend the email verification link.

    Always returns 200 regardless of whether the email is registered
    (anti-enumeration).

    Returns
    -------
    JSONResponse 200
        ``{"message": "If your email is registered, a verification link has been sent"}``
    """
    result = await auth_service.resend_verification(body.email)
    return JSONResponse(status_code=200, content=result)
