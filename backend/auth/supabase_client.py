"""
Supabase async client singleton.

Lazily initialised on first call to ``get_supabase_client()`` so that the
module can be imported safely at startup before environment variables are
loaded (e.g. during test collection or when using python-dotenv).

Requirements: 1.1, 2.1
"""
from __future__ import annotations

from supabase._async.client import AsyncClient, create_client

from backend.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

_client: AsyncClient | None = None


async def get_supabase_client() -> AsyncClient:
    """Return the shared ``AsyncClient`` singleton, creating it on first call.

    Raises
    ------
    RuntimeError
        If ``SUPABASE_URL`` or ``SUPABASE_SERVICE_ROLE_KEY`` is empty or not
        set in the environment.
    """
    global _client

    if _client is not None:
        return _client

    if not SUPABASE_URL:
        raise RuntimeError(
            "SUPABASE_URL is not set. "
            "Add it to your .env file or environment before starting the server."
        )
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. "
            "Add it to your .env file or environment before starting the server."
        )

    try:
        _client = await create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception:
        _client = None  # reset so next request retries instead of reusing a bad state
        raise
    return _client
