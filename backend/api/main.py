"""
Enterprise Compliance Intelligence Platform
FastAPI Entry Point

Hackathon Prototype
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables (override=True ensures .env always wins over stale shell env vars)
load_dotenv(override=True)

from backend.api.routes.cases import router as cases_router
from backend.api.routes.reconciliation import router as reconciliation_router
from backend.api.routes.storage import router as storage_router
from backend.api.routes.workspace_graph import router as ws_graph_router
from backend.api.routes.workspace_query import router as ws_query_router
from backend.api.routes.workspace_report import router as ws_report_router
from backend.api.routes.workspace_settlement_qa import router as ws_settlement_qa_router

# Workspace-aware replacements (user-scoped paths — no global data folders)
from backend.api.routes.workspace_stats import router as ws_stats_router
from backend.api.routes.workspace_upload import router as ws_upload_router
from backend.auth.middleware.jwt_middleware import _get_jwks, get_current_user
from backend.auth.routes.audit import router as audit_router
from backend.auth.routes.auth import router as auth_router
from backend.auth.routes.profile import router as profile_router
from backend.auth.routes.workspace import router as workspace_router
from backend.config import ALLOWED_ORIGINS, OPENAI_API_KEY, SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)

# ------------------------------
# Startup Guards (module-level)
# ------------------------------

if not ALLOWED_ORIGINS:
    logger.critical("ALLOWED_ORIGINS is not set — refusing to start")
    raise SystemExit(1)

if not SUPABASE_JWT_SECRET:
    logger.critical("SUPABASE_JWT_SECRET is not set — refusing to start")
    raise SystemExit(1)

_allowed_origins_list = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
# Ensure the production Vercel origin is always included
_production_origins = {"https://test-inova.vercel.app"}
_allowed_origins_list = list(set(_allowed_origins_list) | _production_origins)
_allowed_origin_regex = r"^https?://(?:localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:[0-9]+)?$"

# ------------------------------
# App
# ------------------------------

app = FastAPI(
    title="Enterprise Compliance Intelligence Platform",
    description="""
AI-powered Multi-Modal Knowledge Graph Synthesis for Enterprise Compliance

Features:
- PDF Upload
- Knowledge Graph Generation
- GraphRAG Query
- Explainable AI
- Evidence-backed Answers
- Compliance Reporting
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ------------------------------
# CORS
# ------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins_list,
    allow_origin_regex=_allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Routers — protected (JWT required)
# ------------------------------

app.include_router(ws_upload_router, prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(ws_query_router,  prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(ws_graph_router,  prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(ws_stats_router,  prefix="/api", dependencies=[Depends(get_current_user)])
app.include_router(
    ws_settlement_qa_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    ws_report_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    cases_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    reconciliation_router,
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)
# NOTE: global_graph_router (graph.py) is intentionally not registered here.
# All graph endpoints are served by workspace_graph.py at /api/graph, which
# is workspace-scoped and authenticated. graph.py is kept only for CLI use.

# ------------------------------
# Routers — auth & workspace
# ------------------------------

app.include_router(auth_router, prefix="/api/auth")
app.include_router(profile_router, prefix="/api/auth")
app.include_router(workspace_router, prefix="/api/workspaces")
app.include_router(audit_router, prefix="/api/workspaces")
app.include_router(storage_router, prefix="/api", dependencies=[Depends(get_current_user)])


# ------------------------------
# Startup: pre-warm JWKS cache
# ------------------------------

@app.on_event("startup")
async def _prewarm_jwks():
    try:
        await _get_jwks()
        logger.info("JWKS cache pre-warmed successfully")
    except Exception as exc:
        logger.warning("JWKS pre-warm failed (will retry on first request): %s", exc)


# ------------------------------
# Health Check
# ------------------------------

@app.get("/")
async def root():
    return {
        "application": "Enterprise Compliance Intelligence Platform",
        "status": "Running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "openai_key_loaded": bool(OPENAI_API_KEY),
        "graph_engine": "MMGraphRAG",
        "prototype": True
    }


@app.get("/memory")
async def memory_usage():
    """Report current process RSS — useful for profiling deployment RAM requirements."""
    try:
        import os
        import psutil
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        return {
            "rss_mb":  round(mem.rss  / 1024**2, 2),
            "vms_mb":  round(mem.vms  / 1024**2, 2),
            "note": "RSS is what cloud providers charge against",
        }
    except ImportError:
        return {"error": "psutil not installed"}
