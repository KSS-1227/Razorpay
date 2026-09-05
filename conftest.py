"""
Root conftest.py — pytest configuration for the compliance/auth unit tests.

Problem
-------
``backend/__init__.py`` eagerly imports ``MMKGBuilder``, which pulls in
``backend.llm.client``, which calls ``get_embed_model()`` at module-level
(inside a decorator argument) and crashes with::

    RuntimeError: sentence-transformers is not installed.

This happens even when a test only imports
``backend.compliance.reconciliation_engine`` — Python's package-import
machinery runs ``backend/__init__.py`` first.

Fix
---
Insert a lightweight stub for ``backend`` into ``sys.modules`` *before* any
test module is imported.  The stub uses the real ``backend/`` directory as its
``__path__`` so Python's importer can still find every sub-package
(``backend.compliance``, ``backend.cockroach_graph_storage``, …) — it just
skips the broken ``__init__.py`` body.

We also pre-stub the two modules that crash at import time:
- ``backend.llm.client``: calls ``get_embed_model()`` at module level inside a
  decorator argument — no way to patch around it at collection time.
- ``backend.config.settings``: imported by ``llm.client``; stubbing it prevents
  a second crash even if the import order changes.

``sys.modules`` is not cleaned up — that's intentional and safe for a test
session (stubs are process-scoped, not test-scoped).
"""
import sys
import types
from pathlib import Path

# Absolute path to the real backend/ directory so sub-package discovery works.
_BACKEND_DIR = str(Path(__file__).parent / "backend")


def _install_stubs() -> None:
    """Install minimal stubs that prevent the ML import chain from firing."""

    # Only stub when sentence_transformers is absent.  In a full-dependency
    # environment (CI with all extras installed) we want the real imports.
    try:
        import sentence_transformers  # noqa: F401
        return
    except ImportError:
        pass

    # ------------------------------------------------------------------ #
    # backend  (top-level package)                                         #
    # ------------------------------------------------------------------ #
    # We must set __path__ to the *real* directory so that sub-packages
    # like backend.compliance and backend.cockroach_graph_storage are still
    # importable via the normal filesystem finder.
    if "backend" not in sys.modules:
        pkg = types.ModuleType("backend")
        pkg.__path__ = [_BACKEND_DIR]      # <-- key: real path, not []
        pkg.__package__ = "backend"
        pkg.__spec__ = None
        sys.modules["backend"] = pkg

    # ------------------------------------------------------------------ #
    # backend.llm  (sub-package)                                           #
    # ------------------------------------------------------------------ #
    if "backend.llm" not in sys.modules:
        llm_pkg = types.ModuleType("backend.llm")
        llm_pkg.__path__ = [str(Path(_BACKEND_DIR) / "llm")]
        llm_pkg.__package__ = "backend.llm"
        llm_pkg.__spec__ = None
        # Expose every name that backend.llm.__init__ re-exports from client.
        # These are imported directly by backend.ingestion.image_utils,
        # backend.graph.fusion, backend.graph.text2graph, etc.
        # Stubs return the minimal valid fake so callers don't crash on import.
        async def _noop_llm(*a, **kw):
            return ""
        async def _noop_json(*a, **kw):
            return {}
        async def _noop_json_list(*a, **kw):
            return []
        async def _noop_mm(*a, **kw):
            return ""

        llm_pkg.get_llm_response       = _noop_llm        # type: ignore[attr-defined]
        llm_pkg.get_mmllm_response     = _noop_mm         # type: ignore[attr-defined]
        llm_pkg.model_if_cache         = _noop_llm        # type: ignore[attr-defined]
        llm_pkg.multimodel_if_cache    = _noop_mm         # type: ignore[attr-defined]
        llm_pkg.normalize_to_json      = _noop_json       # type: ignore[attr-defined]
        llm_pkg.normalize_to_json_list = _noop_json_list  # type: ignore[attr-defined]
        sys.modules["backend.llm"] = llm_pkg

    # ------------------------------------------------------------------ #
    # backend.llm.client  (crashes at module level via decorator arg)      #
    # ------------------------------------------------------------------ #
    if "backend.llm.client" not in sys.modules:
        client = types.ModuleType("backend.llm.client")
        # Provide enough surface area for any import-time attribute lookups.
        client.local_embedding = None   # type: ignore[attr-defined]
        client.model_if_cache  = None   # type: ignore[attr-defined]
        sys.modules["backend.llm.client"] = client

    # ------------------------------------------------------------------ #
    # backend.config  (sub-package)                                        #
    # ------------------------------------------------------------------ #
    if "backend.config" not in sys.modules:
        cfg_pkg = types.ModuleType("backend.config")
        cfg_pkg.__path__ = [str(Path(_BACKEND_DIR) / "config")]
        cfg_pkg.__package__ = "backend.config"
        cfg_pkg.__spec__ = None
        sys.modules["backend.config"] = cfg_pkg

    # ------------------------------------------------------------------ #
    # backend.config.settings  (imports sentence_transformers at top)      #
    # ------------------------------------------------------------------ #
    if "backend.config.settings" not in sys.modules:
        settings = types.ModuleType("backend.config.settings")
        settings.get_embed_model = lambda: None   # type: ignore[attr-defined]
        settings.API_KEY        = ""
        settings.API_BASE       = ""
        settings.MM_API_KEY     = ""
        settings.MM_API_BASE    = ""
        settings.MODEL_NAME     = ""
        settings.MM_MODEL_NAME  = ""
        # Also stub names imported by backend/config/__init__.py if it exists
        settings.ALLOWED_ORIGINS      = ""
        settings.OPENAI_API_KEY       = ""
        settings.SUPABASE_JWT_SECRET  = ""
        # Additional settings consumed by backend.graph.text2graph and similar
        settings.ENTITY_EXTRACT_MAX_GLEANING = 1
        settings.MAX_TOKENS          = 4096
        settings.WORKING_DIR         = "/tmp"
        sys.modules["backend.config.settings"] = settings

    # ------------------------------------------------------------------ #
    # jose  (python-jose — JWT library used by auth middleware)            #
    # Not installed in this dev environment; stub so auth modules can be   #
    # imported and then patched in tests without calling real JWT logic.   #
    # ------------------------------------------------------------------ #
    if "jose" not in sys.modules:
        jose_stub = types.ModuleType("jose")
        # Provide the exception classes and jwt object that jwt_middleware imports
        jose_stub.JWTError           = Exception
        jose_stub.ExpiredSignatureError = Exception
        jwt_stub = types.ModuleType("jose.jwt")
        jwt_stub.decode = lambda *a, **kw: {}   # type: ignore[attr-defined]
        jose_stub.jwt   = jwt_stub
        sys.modules["jose"]     = jose_stub
        sys.modules["jose.jwt"] = jwt_stub


_install_stubs()
