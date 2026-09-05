"""Windows-safe local entry point for the FastAPI application.

Psycopg's async connections require a selector event loop on Windows.  Uvicorn
creates its event loop before importing ``backend.api.main`` when launched as
``uvicorn backend.api.main:app``; therefore the policy must be selected here,
before starting Uvicorn.
"""
from __future__ import annotations

import asyncio
import os
import sys

import uvicorn


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    uvicorn.run(
        "backend.api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
