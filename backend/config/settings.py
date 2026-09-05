"""
Runtime configuration for the Enterprise Compliance Intelligence Platform.
...
"""
import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env BEFORE any os.environ.get() calls so env vars are available
# regardless of import order (uvicorn reloader imports config before main.py).
load_dotenv()

# ============ LLM Configuration ============
# One server-side OpenAI API key powers text, vision, and transcription.
# The LLM_/MM_ names remain backwards-compatible deployment overrides.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")

# Text LLM — entity extraction, relation building, RAG answers
API_KEY    = OPENAI_API_KEY
API_BASE   = os.environ.get("LLM_API_BASE",   "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("LLM_MODEL_NAME") or os.environ.get("OPENAI_MODEL", "gpt-4o")

# Multimodal LLM — image understanding, visual entity extraction, scene graphs
# Uses the same OpenAI key and endpoint; gpt-4o supports vision natively.
MM_API_KEY    = os.environ.get("MM_API_KEY") or OPENAI_API_KEY
MM_API_BASE   = os.environ.get("MM_API_BASE",   "https://api.openai.com/v1")
MM_MODEL_NAME = os.environ.get("MM_MODEL_NAME") or os.environ.get("OPENAI_MODEL", "gpt-4o")

# ============ Embedding Model ============
_default_embed_dir = (
    "./models/all-MiniLM-L6-v2"
    if os.path.exists("./models/all-MiniLM-L6-v2")
    else "sentence-transformers/all-MiniLM-L6-v2"
)
EMBEDDING_MODEL_DIR = os.environ.get("EMBEDDING_MODEL_DIR", _default_embed_dir)

# Sentinel kept for backward-compat imports (e.g. `from backend.config import EMBED_MODEL`).
# Always use get_embed_model() when you need the actual model instance.
EMBED_MODEL = None

_embed_model_instance = None


def get_embed_model():
    """Return the shared SentenceTransformer instance, loading it on first call.

    Lazy-loading prevents the ~90 MB model download from blocking the FastAPI
    startup sequence. Auth, workspace, and case endpoints all start immediately;
    the model is only loaded when the first document upload or query arrives.

    Raises
    ------
    RuntimeError
        If sentence-transformers is not installed or the model cannot be loaded.
    """
    global _embed_model_instance
    if _embed_model_instance is not None:
        return _embed_model_instance

    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        ) from exc

    logger.info("Loading embedding model from %s …", EMBEDDING_MODEL_DIR)
    try:
        _embed_model_instance = SentenceTransformer(EMBEDDING_MODEL_DIR, device="cpu")
        logger.info("Embedding model loaded successfully.")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load embedding model from '{EMBEDDING_MODEL_DIR}': {exc}. "
            "Check that the model path or HuggingFace model name is correct and "
            "that you have an active internet connection for the first download."
        ) from exc

    return _embed_model_instance


# ============ Directory Paths ============
INPUT_PDF_PATH = os.environ.get("INPUT_PDF_PATH", "data/input/2020.acl-main.45.pdf")
CACHE_PATH     = os.environ.get("CACHE_PATH",     "data/cache")
WORKING_DIR    = os.environ.get("WORKING_DIR",    "data/working")
OUTPUT_DIR     = os.environ.get("OUTPUT_DIR",     "data/output")
MMKG_NAME      = os.environ.get("MMKG_NAME",      "example_mmkg")

# ============ Processing Parameters ============
ENTITY_EXTRACT_MAX_GLEANING  = int(os.environ.get("ENTITY_EXTRACT_MAX_GLEANING",  "0"))
ENTITY_SUMMARY_MAX_TOKENS    = int(os.environ.get("ENTITY_SUMMARY_MAX_TOKENS",    "500"))
SUMMARY_CONTEXT_MAX_TOKENS   = int(os.environ.get("SUMMARY_CONTEXT_MAX_TOKENS",   "10000"))
USE_MINERU = os.environ.get("USE_MINERU", "true").lower() in ("1", "true", "yes")

# ============ RAG Retrieval Configuration ============
class QueryParam:
    top_k: int = 5
    response_type: str = "Detailed System-like Response"
    local_max_token_for_local_context: int = 4000
    number_of_mmentities: int = 3
    local_max_token_for_text_unit: int = 4000

RETRIEVAL_THRESHOLD: float = 0.2

# ============ Audio / OpenAI Whisper Configuration ============
# Audio transcription uses the same OpenAI key as the LLM clients.

# ============ Auth / Supabase Configuration ============
SUPABASE_URL              = os.environ.get("SUPABASE_URL",              "")
SUPABASE_ANON_KEY         = os.environ.get("SUPABASE_ANON_KEY",         "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_JWT_SECRET       = os.environ.get("SUPABASE_JWT_SECRET",       "")

# Derived automatically — do NOT set this in the environment
SUPABASE_JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

# Comma-separated list of allowed CORS origins, e.g. "https://app.example.com,https://admin.example.com"
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "")
