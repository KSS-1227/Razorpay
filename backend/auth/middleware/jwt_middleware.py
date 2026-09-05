"""
JWT validation middleware for the Enterprise Compliance Intelligence Platform.

Validates Supabase-issued JWTs on every protected request, injects an
``AuthContext`` via FastAPI's ``Depends()`` mechanism, and enforces workspace
membership when the ``X-Workspace-ID`` header is present.

JWKS keys are cached in-memory for 5 minutes (JWKS_TTL_SECONDS) to avoid
a remote call on every request while still picking up key rotation promptly.

Requirements: 3.1–3.4, 4.2–4.4, 9.1–9.5
"""
from __future__ import annotations

import base64
import json
import logging
import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel

from backend.auth.supabase_client import get_supabase_client
from backend.config import SUPABASE_JWKS_URL, SUPABASE_JWT_SECRET, SUPABASE_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level JWKS cache
# ---------------------------------------------------------------------------
_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
JWKS_TTL_SECONDS = 300  # 5 minutes

# ---------------------------------------------------------------------------
# Valid roles (must match the DB constraint)
# ---------------------------------------------------------------------------
_VALID_ROLES: frozenset[str] = frozenset({"Admin", "Analyst", "Viewer"})

# ---------------------------------------------------------------------------
# AuthContext — injected into every protected handler
# ---------------------------------------------------------------------------


class AuthContext(BaseModel):
    """Decoded, validated identity extracted from the Supabase JWT."""

    user_id: str      # sub claim (UUID)
    role: str         # role claim: Admin | Analyst | Viewer
    workspace_id: str  # from X-Workspace-ID header, validated against DB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _peek_token_alg(token: str) -> str:
    """Return the `alg` value from the JWT header without full verification."""
    try:
        header_b64 = token.split(".")[0]
        # Add padding
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        return header.get("alg", "").upper()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# JWKS helpers
# ---------------------------------------------------------------------------


async def _get_jwks() -> dict[str, Any]:
    """Return the cached JWKS, refreshing from Supabase when stale.

    Behaviour on network failure:
    - If a stale cache exists, log the error and return stale keys.
    - If the cache is empty, log the error and re-raise so the caller can
      surface an HTTP 503.
    """
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < JWKS_TTL_SECONDS:
        return _jwks_cache

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(SUPABASE_JWKS_URL)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_fetched_at = now
            return _jwks_cache
    except Exception as exc:
        logger.error("JWKS endpoint unreachable: %s", exc)
        if _jwks_cache:
            # Serve stale keys rather than returning a 503
            return _jwks_cache
        raise  # Will surface as HTTP 503 in get_current_user


# ---------------------------------------------------------------------------
# FastAPI dependency — main entry point
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> AuthContext:
    """Validate the Bearer JWT and return an AuthContext.

    Raises HTTPException for all auth/authz failures with the exact error
    shapes specified in the design document.
    """

    # ── 1. Require a Bearer token ──────────────────────────────────────────
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "error": "missing_token",
                "message": "Authorization header with Bearer token is required",
            },
        )

    token: str = credentials.credentials

    # ── 2. Peek at the token header to decide which path to take ──────────
    token_alg = _peek_token_alg(token)
    use_hs256 = bool(SUPABASE_JWT_SECRET) and token_alg in ("", "HS256")
    use_jwks  = token_alg in ("RS256", "ES256", "")  # "" = try both

    # ── 3. Fast-path: HS256 with the JWT secret ───────────────────────────
    #    Only attempt if the token header actually declares HS256 (or is
    #    unreadable). Newer Supabase projects use ES256 — attempting HS256
    #    on those tokens causes python-jose to raise "alg not allowed".
    payload: dict[str, Any] | None = None
    last_error: Exception | None = None

    if use_hs256:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
                issuer=f"{SUPABASE_URL}/auth/v1",
            )
        except (ExpiredSignatureError, JWTError) as exc:
            logger.warning("HS256 decode failed: %s | token_prefix=%s", exc, token[:40])
            last_error = exc

    # ── 4. Fallback / primary: ES256/RS256 via JWKS ───────────────────────
    if payload is None and use_jwks:
        try:
            jwks = await _get_jwks()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"error": "auth_service_unavailable"},
            ) from exc

        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256", "ES256"],
                options={"verify_aud": False},
                issuer=f"{SUPABASE_URL}/auth/v1",
            )
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail={"error": "token_expired", "message": "Token has expired"},
            ) from None
        except JWTError as exc:
            logger.warning("JWKS decode failed: %s", exc)
            last_error = exc

    if payload is None:
        if isinstance(last_error, ExpiredSignatureError):
            raise HTTPException(
                status_code=401,
                detail={"error": "token_expired", "message": "Token has expired"},
            )
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Token signature is invalid"},
        )

    # ── 4. Extract user_id (sub) ──────────────────────────────────────────
    user_id: str = payload.get("sub", "")

    # ── 5. Extract and validate role ─────────────────────────────────────
    # Supabase puts "authenticated" in the top-level `role` claim.
    # The app-specific role (Admin / Analyst / Viewer) lives in app_metadata.
    app_metadata: dict = payload.get("app_metadata") or {}
    role: str | None = app_metadata.get("role") or payload.get("role")
    # Fresh Supabase users have role="authenticated" in the top-level claim.
    # Default them to Viewer so they can use the app immediately after signup.
    if role is None or role not in _VALID_ROLES:
        role = "Viewer"

    # ── 6. Resolve workspace from header ─────────────────────────────────
    workspace_id: str = request.headers.get("X-Workspace-ID", "")

    if workspace_id:
        # Validate that an active membership record exists for (user_id, workspace_id)
        try:
            supabase = await get_supabase_client()
            result = (
                await supabase
                .table("workspace_members")
                .select("member_id")
                .eq("user_id", user_id)
                .eq("workspace_id", workspace_id)
                .eq("membership_status", "active")
                .maybe_single()
                .execute()
            )
            if result.data is None:
                raise HTTPException(
                    status_code=403,
                    detail={"error": "unrecognised_role"},
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Workspace membership check failed for user=%s workspace=%s: %s",
                user_id,
                workspace_id,
                exc,
            )
            raise HTTPException(
                status_code=503,
                detail={"error": "auth_service_unavailable"},
            ) from exc

    return AuthContext(user_id=user_id, role=role, workspace_id=workspace_id)
