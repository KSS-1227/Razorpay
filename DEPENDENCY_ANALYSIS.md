# Dependency Analysis — Enterprise Compliance Intelligence Platform

**Date**: August 1, 2026  
**Analyst**: Kiro Lead AI Architect  
**Basis**: Static import analysis of all `src/**/*.py` files + product requirements

---

## Context & Methodology

This analysis answers a single question for each dependency:

> *Does the Enterprise Compliance Intelligence Platform need this package to ingest enterprise documents, build a compliance knowledge graph, perform GraphRAG retrieval, and produce explainable, evidence-backed answers?*

Imports were traced file-by-file from actual source code. Nothing is assumed.

**Three tiers are defined:**

| Tier | Meaning |
|------|---------|
| **CORE** | Required right now. The reused pipeline components cannot run without it. |
| **OPTIONAL** | Required eventually for specific features, but the platform can start and run basic flows without it today. |
| **RESEARCH ONLY** | Only appears in benchmark/eval scripts (`eval_reference/`). Zero role in the enterprise product. |

---

## Part 1 — Dependency Table

| # | Package | Imported In | Purpose in Codebase | Tier | Required Now? | Required Later? | Research Only? | Replacement / Notes |
|---|---------|-------------|---------------------|------|---------------|-----------------|----------------|---------------------|
| 1 | `openai` | `src/llm/client.py` | All LLM and MLLM API calls (text extraction, entity alignment, RAG generation) | **CORE** | ✅ Yes | ✅ Yes | ❌ No | Provider-agnostic; can swap to `anthropic`, `google-generativeai`, etc. via parameter changes |
| 2 | `numpy` | `src/core/base.py`, `src/llm/client.py`, `src/graph/fusion.py`, `src/retrieval/query.py` | Embedding arrays, spectral clustering matrices, cosine similarity computation | **CORE** | ✅ Yes | ✅ Yes | ❌ No | No replacement. Fundamental. |
| 3 | `networkx` | `src/core/storage.py`, `src/builder.py`, `src/retrieval/query.py`, `src/graph/fusion.py` | Knowledge graph in-memory representation, GraphML read/write, node/edge operations | **CORE** | ✅ Yes | ✅ Yes | ❌ No | No replacement. The entire KG storage abstraction is built on NetworkX. |
| 4 | `scikit-learn` | `src/graph/fusion.py`, `src/retrieval/query.py` | `cosine_similarity` for RAG node retrieval; `DBSCAN` for spectral clustering in image-entity alignment | **CORE** | ✅ Yes | ✅ Yes | ❌ No | `cosine_similarity` could be replaced with a numpy dot product. `DBSCAN` is harder to replace without rewriting fusion. |
| 5 | `tiktoken` | `src/core/base.py`, `src/preprocessing/pdf_preprocessing.py` | Token counting for text chunking (sliding window, overlap, max token size) | **CORE** | ✅ Yes | ✅ Yes | ❌ No | Tied to GPT-4o tokenizer. If using a non-OpenAI model, can swap to `transformers.AutoTokenizer`. |
| 6 | `tqdm` | `src/graph/fusion.py`, `src/graph/img2graph.py`, `src/graph/text2graph.py`, `src/preprocessing/pdf_preprocessing.py` | Progress bars for document ingestion and graph construction pipelines | **CORE** | ✅ Yes | ✅ Yes | ❌ No | Can be removed with minimal refactoring if a different progress mechanism is preferred. |
| 7 | `Pillow` (PIL) | `src/graph/img2graph.py`, `src/preprocessing/pdf_preprocessing.py` | Opening, resizing, and compressing images extracted from PDFs before sending to MLLM | **CORE** | ✅ Yes | ✅ Yes | ❌ No | No practical replacement for image handling in Python. |
| 8 | `sentence-transformers` | `src/parameter.py` | Loads `all-MiniLM-L6-v2` for local text embeddings used in RAG node retrieval and spectral clustering | **CORE** | ✅ Yes | ✅ Yes | ❌ No | Can be replaced with an API-based embedding (e.g., `openai.embeddings`). Local model avoids API cost. |
| 9 | `pymupdf` (fitz) | `src/preprocessing/pdf_preprocessing.py` — conditional import inside `_process_pymupdf()` | PDF text extraction and image extraction fallback when MinerU is unavailable | **CORE** | ✅ Yes | ✅ Yes | ❌ No | This is the fallback parser. MinerU is preferred but optional. At least one parser is mandatory. |
| 10 | `opencv-python` (cv2) | `src/graph/img2graph.py` | YOLO mask processing: drawing contours, bitwise masking, cropping segmented objects from images | **CORE** | ✅ Yes | ✅ Yes | ❌ No | Only needed when YOLO segmentation is active (`segmentation=True`). If compliance docs have no scene images, this path is rarely triggered. |
| 11 | `ultralytics` | `src/graph/img2graph.py` | Loads YOLOv8 segmentation model to isolate objects in images (charts, diagrams, photos) before MLLM analysis | **CORE** | ✅ Yes | ✅ Yes | ❌ No | For compliance documents (PDFs with tables/charts), YOLO segmentation is typically `False`. The YOLO path can be disabled by setting `segmentation=False` at image description time. |
| 12 | `flask` | `src/visualization/server.py` | Serves the interactive knowledge graph explorer web UI | **OPTIONAL** | ⚠️ Not for MVP | ✅ Yes | ❌ No | Only needed when running the visualization server (`-s` flag). Not required for ingestion or query pipeline. |
| 13 | `flask-cors` | `src/visualization/server.py` | CORS headers for the Flask visualization server API | **OPTIONAL** | ⚠️ Not for MVP | ✅ Yes | ❌ No | Paired with Flask. Same deferral applies. |
| 14 | `graspologic` | `src/core/storage.py` — line 224, inside `stable_largest_connected_component()` | Provides `largest_connected_component()` utility for graph stabilization | **OPTIONAL** | ⚠️ Not for MVP | ⚠️ Maybe | ❌ No | **This method has zero callers in the current codebase.** It is dead code carried over from `nano-graphrag`. Can be safely excluded until explicitly needed. NetworkX has its own `connected_components()`. |
| 15 | `mineru` (CLI tool) | `src/preprocessing/pdf_preprocessing.py` — `shutil.which('mineru')` + `subprocess.run()` | High-quality PDF parsing: complex layouts, tables, math, multi-column. Preferred over PyMuPDF for dense compliance documents | **OPTIONAL** | ⚠️ Recommended | ✅ Yes | ❌ No | Not a pip package — installed separately. System falls back to PyMuPDF automatically if not found. **Highly recommended for compliance PDFs.** |
| 16 | `torch` | Pulled in as transitive dependency by `sentence-transformers` | PyTorch runtime for the local embedding model | **CORE** (transitive) | ✅ Yes (auto) | ✅ Yes | ❌ No | Installed automatically with `sentence-transformers`. ~2.5GB on disk. If using API-based embeddings instead, can be eliminated. |
| 17 | `transformers` | Pulled in by `sentence-transformers` | HuggingFace model loading infrastructure for the embedding model | **CORE** (transitive) | ✅ Yes (auto) | ✅ Yes | ❌ No | Same as torch — transitive. |
| 18 | `scipy` | Pulled in by `scikit-learn`, `graspologic` | Scientific math (used internally by sklearn for DBSCAN, cosine_similarity) | **CORE** (transitive) | ✅ Yes (auto) | ✅ Yes | ❌ No | Transitive. Not directly imported in src/. |
| 19 | `tokenizers` | Pulled in by `transformers` | Fast tokenization used internally by HuggingFace | **CORE** (transitive) | ✅ Yes (auto) | ✅ Yes | ❌ No | Transitive only. |
| 20 | `torch` (eval scripts) | `eval_reference/docbench_eval/eval_llm.py`, `eval_reference/mmlongbench_eval/run.py` | GPU inference for Ovis1.6-Gemma2-27B model on HPC cluster | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ Yes | Entirely irrelevant to the enterprise product. The enterprise product uses API-based LLMs. |
| 21 | `transformers` (eval scripts) | `eval_reference/docbench_eval/QA.py` | Loading `AutoModelForCausalLM` for Ovis multimodal model on HPC | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ Yes | Same as above. HPC cluster research only. |
| 22 | `umap-learn` | Transitive from `graspologic` | Dimensionality reduction used internally by graspologic | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ No — but only relevant if graspologic is used | If graspologic is excluded, this disappears entirely. |
| 23 | `gensim` | Transitive from `graspologic` | Word2Vec / topic modeling used by graspologic internals | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ No — but only relevant if graspologic is used | Same — only pulled in by graspologic. |
| 24 | `numba` | Transitive from `graspologic → hyppo` | JIT compilation used by hyppo (statistical testing library) | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ No — but only relevant if graspologic is used | ~40MB binary. Completely unnecessary for compliance platform. |
| 25 | `llvmlite` | Transitive from `numba` | LLVM backend for numba | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ No — but only relevant if graspologic is used | ~40MB binary. Disappears if graspologic is excluded. |
| 26 | `statsmodels` | Transitive from `graspologic` | Statistical modeling library | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ No — but only relevant if graspologic is used | Irrelevant to compliance platform. |
| 27 | `POT` (Python Optimal Transport) | Transitive from `graspologic` | Optimal transport algorithms for graph matching | **RESEARCH ONLY** | ❌ No | ❌ No | ✅ No | Graph matching is a research use case not needed in compliance RAG. |
| 28 | `polars` | Transitive from `ultralytics` | Fast dataframe library for YOLO evaluation metrics | **OPTIONAL** (transitive) | ⚠️ Auto | ⚠️ Auto | ❌ No | Pulled in by ultralytics. Not directly used in `src/`. |


---

## Part 2 — Tiered Summary

### CORE — Install First, Non-Negotiable

These 11 packages are directly imported by the reused pipeline components. The compliance platform cannot ingest a single document without them.

```
openai              # All LLM calls
numpy               # Embedding math
networkx            # Knowledge graph
scikit-learn        # Cosine similarity + DBSCAN clustering
tiktoken            # Text chunking token counting
tqdm                # Pipeline progress
Pillow              # Image handling
sentence-transformers  # Local text embeddings + pulls in torch/transformers
pymupdf             # PDF parsing (fallback, always needed)
opencv-python       # YOLO mask processing
ultralytics         # YOLO object detection + segmentation
```

**Transitive packages installed automatically with the above:**
`torch`, `transformers`, `tokenizers`, `scipy`, `huggingface-hub`, `safetensors`, `torchvision`, `sympy`, `pyyaml`, `requests`, `httpx`, `pydantic`, `regex`, `filelock`, `fsspec`, `colorama`, `tqdm`, `packaging`, `click`, `jinja2`, `markupsafe`, `anyio`, `sniffio`, `certifi`, `urllib3`, `idna`, `charset-normalizer`

---

### OPTIONAL — Defer Until Feature Is Needed

```
flask               # Visualization server — defer until UI sprint
flask-cors          # Visualization server — defer with flask
graspologic         # Dead code in current codebase — defer indefinitely
mineru              # Better PDF parsing — install manually when ready
```

**Why defer graspologic specifically:**
The only usage is inside `NetworkXStorage.stable_largest_connected_component()` which has **no callers** in the entire codebase. It was carried over from the upstream `nano-graphrag` project. Installing it pulls in 8 additional heavy packages: `umap-learn`, `gensim`, `hyppo`, `numba`, `llvmlite`, `statsmodels`, `POT`, `beartype`. Total extra disk: ~300MB+. Zero benefit until someone explicitly calls that method.

---

### RESEARCH ONLY — Never Install for Enterprise Product

These packages exist exclusively in `eval_reference/` which is benchmark evaluation code for two academic datasets (DocBench, MMLongBench) on an HPC cluster. They have no path into the enterprise product.

```
# From eval_reference/docbench_eval/QA.py and eval_reference/mmlongbench_eval/run.py
torch          (as standalone GPU inference, not the transitive one from sentence-transformers)
transformers   (for AutoModelForCausalLM — loading 27B Ovis model)
```

Note: `torch` and `transformers` ARE installed as transitives from `sentence-transformers` (CORE). The distinction is that loading a 27B local model for HPC cluster experiments is research-only. Using them as embedding infrastructure is CORE.

---

## Part 3 — What Can Be Safely Omitted for Initial Development

For an MVP sprint that demonstrates document ingestion → graph construction → compliance Q&A:

### Omit entirely from `requirements.txt`:

| Package | Why Safe to Omit |
|---------|-----------------|
| `flask` | Visualization is a convenience feature, not required for the core pipeline |
| `flask-cors` | Depends on flask |
| `graspologic` | Dead code — zero callers in codebase. Removes 8 heavy transitive packages. |

### Defer from installation (install manually when ready):

| Package | When to Add |
|---------|------------|
| `mineru` | When you onboard the first batch of complex compliance PDFs with multi-column layouts, tables with merged cells, or scanned documents. Until then, PyMuPDF handles basic PDFs fine. |

### Never install:

| Package | Reason |
|---------|--------|
| `torch` as standalone (>= 2GB GPU runtime) | The enterprise product uses API-based LLMs. The only torch needed is the CPU embedding inference pulled by `sentence-transformers`, which is handled automatically. |
| Any `eval_reference/` dependencies | Research code, irrelevant to product |

---

## Part 4 — New Dependencies the Enterprise Platform Needs (Not in Codebase)

The compliance platform requires capabilities beyond what the research codebase provides. These are **net-new** dependencies that will be needed as the platform is built:

| Package | Purpose | When |
|---------|---------|------|
| `python-dotenv` | Load API keys from `.env` file securely | Immediately |
| `openpyxl` or `xlrd` | Read Excel tables (`.xlsx`/`.xls`) — compliance data | Sprint 1 |
| `pydantic` | Already transitive — but should be explicit for config validation and compliance data schemas | Immediately |
| `pandas` | Tabular data handling for Excel/CSV compliance reports | Sprint 1 |
| `python-docx` | Read Word documents (`.docx`) — policy documents | Sprint 1-2 |
| `faster-whisper` or `openai-whisper` | Transcribe audio meeting logs | Sprint 2-3 |
| `pytesseract` or `azure-cognitiveservices-vision-computervision` | OCR for scanned documents | Sprint 2 |
| `celery` + `redis` | Async task queue for long-running ingestion jobs in production | Sprint 3 |
| `sqlalchemy` | Persistent storage for compliance records and audit trail | Sprint 2 |
| `loguru` or structured logging | Production-grade logging with trace IDs for audit | Sprint 1 |
| `pytest` | Test framework | Immediately |
| `httpx` | Already transitive — explicit for async HTTP calls to compliance APIs | Sprint 2 |

---

## Part 5 — Recommended Minimal `requirements.txt` for Enterprise Platform MVP

```
# ============================================================
# Enterprise Compliance Intelligence Platform
# Minimal requirements for MVP
# Python 3.12.x
# ============================================================

# --- Secrets & Config ---
python-dotenv>=1.0.0

# --- LLM API ---
openai>=1.30.0,<2.0.0

# --- Embeddings (local, CPU) ---
sentence-transformers>=3.0.0,<4.0.0

# --- Knowledge Graph ---
networkx>=3.3,<4.0

# --- Machine Learning ---
scikit-learn>=1.4.2,<2.0.0
numpy>=1.26.4,<2.0.0

# --- Token Counting ---
tiktoken>=0.7.0,<1.0.0

# --- Image Processing ---
Pillow>=10.3.0,<12.0.0
opencv-python==4.9.0.80

# --- Object Detection (YOLO for diagram/image entity extraction) ---
ultralytics>=8.2.0,<9.0.0

# --- PDF Parsing ---
pymupdf>=1.24.5,<2.0.0

# --- Progress ---
tqdm>=4.66.4,<5.0.0

# --- Data Handling ---
pandas>=2.2.0,<4.0.0
openpyxl>=3.1.0,<4.0.0

# --- Testing ---
pytest>=8.0.0,<9.0.0

# ============================================================
# DEFERRED (add when needed):
# flask>=3.0.3                  # visualization server
# flask-cors>=4.0.1             # visualization server
# graspologic>=3.3.0            # dead code — add only if needed
# python-docx>=1.0.0            # Word document ingestion
# faster-whisper>=1.0.0         # audio meeting transcription
# ============================================================
```

---

## Part 6 — Dependency Conflict Warning

**numpy version conflict between `graspologic` and `opencv-python`:**

- `graspologic>=3.3.0` requires `numpy<2.0.0`
- `opencv-python>=4.10.0` requires `numpy>=2.0.0`

**Resolution**: If graspologic is included, pin `opencv-python==4.9.0.80` (the last version compatible with numpy 1.x). This is what the earlier installation attempt found.

**Recommendation**: Exclude graspologic from MVP requirements and use `numpy>=1.26.4,<2.0.0` to maintain a clean constraint. The dead code in `NetworkXStorage.stable_largest_connected_component()` should simply be removed from the source.

---

## Part 7 — Decision Summary

```
INSTALL NOW (MVP):     openai, sentence-transformers, networkx, scikit-learn,
                       numpy, tiktoken, Pillow, opencv-python, ultralytics,
                       pymupdf, tqdm, pandas, openpyxl, python-dotenv, pytest

DEFER:                 flask, flask-cors, graspologic, mineru,
                       python-docx, faster-whisper, pytesseract

NEVER INSTALL:         eval_reference/ dependencies (torch as standalone,
                       transformers as AutoModelForCausalLM, umap-learn,
                       gensim, numba, llvmlite, statsmodels, POT)
```

---

*Awaiting your approval before any installation or file modification.*
