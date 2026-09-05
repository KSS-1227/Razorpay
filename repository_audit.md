# MMGraphRAG Repository Audit Report

**Date**: August 1, 2026  
**Auditor**: Kiro AI Senior Engineer  
**Scope**: Complete static analysis — no code was modified.

---

## Table of Contents

1. [Repository Overview](#1-repository-overview)
2. [Complete Folder & File Structure](#2-complete-folder--file-structure)
3. [Module Descriptions](#3-module-descriptions)
4. [File Classification (KEEP / MODIFY / REMOVE / UNKNOWN)](#4-file-classification)
5. [Detected Code Categories](#5-detected-code-categories)
6. [Dependency Discovery](#6-dependency-discovery)
7. [Generated requirements.txt](#7-generated-requirementstxt)
8. [Missing Dependencies](#8-missing-dependencies)
9. [Cleanup Recommendations](#9-cleanup-recommendations)
10. [Suggested Architecture Improvements](#10-suggested-architecture-improvements)

---

## 1. Repository Overview

MMGraphRAG is a **multi-modal knowledge graph RAG framework** that builds a fused knowledge graph from PDF documents by:

1. Parsing PDFs with MinerU or PyMuPDF
2. Extracting text entities/relations via LLM (text2graph)
3. Extracting image entities via YOLO + MLLM (img2graph)
4. Fusing text and image KGs via spectral clustering + LLM alignment (fusion)
5. Answering queries via a local GraphRAG pipeline with multimodal augmentation

The codebase is a **research prototype** undergoing active refactoring. It previously defaulted to Alibaba DashScope (Qwen) APIs but now uses OpenAI-compatible endpoints by default (configurable via environment variables).

**Language**: Python 3.10+  
**No** `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, `Pipfile`, `environment.yml`, or `uv.lock` was found — dependency management is entirely manual.

---

## 2. Complete Folder & File Structure

```
MMGraphRAG/
├── .git/                                   # Version control (ignore)
├── .gitignore                              # Only contains .DS_Store
├── LICENSE                                 # License file
├── README.md                               # English documentation
├── README_zh.md                            # Chinese documentation
├── main.py                                 # CLI entry point
│
├── src/                                    # Core source code
│   ├── __init__.py                         # Exports MMKGBuilder
│   ├── builder.py                          # Main pipeline orchestrator
│   ├── parameter.py                        # All global config & hyperparameters
│   │
│   ├── core/                               # Shared utilities & abstractions
│   │   ├── __init__.py
│   │   ├── base.py                         # Utility functions (hashing, tokens, logging)
│   │   ├── prompt.py                       # All LLM prompt templates (~668 lines)
│   │   └── storage.py                      # KV store & graph store abstractions
│   │
│   ├── graph/                              # Knowledge graph construction
│   │   ├── __init__.py
│   │   ├── text2graph.py                   # Text → KG extraction pipeline
│   │   ├── img2graph.py                    # Image → KG extraction pipeline
│   │   ├── fusion.py                       # Text KG + Image KG fusion
│   │   ├── utils.py                        # Shared entity/edge merge helpers
│   │   └── yolov8n-seg.pt                  # YOLO model weights (~6MB binary)
│   │
│   ├── llm/                                # LLM client layer
│   │   ├── __init__.py
│   │   └── client.py                       # Sync/async OpenAI clients + JSON utils
│   │
│   ├── preprocessing/                      # PDF parsing & chunking
│   │   ├── __init__.py
│   │   └── pdf_preprocessing.py            # PyMuPDF + MinerU preprocessing
│   │
│   ├── retrieval/                          # RAG query engine
│   │   ├── __init__.py
│   │   └── query.py                        # GraphRAGQuery class
│   │
│   └── visualization/                      # Web visualization server
│       ├── graph_explorer.html             # Frontend (force-directed graph)
│       └── server.py                       # Flask API server
│
├── examples/                               # Demo & sample data
│   ├── docqa_example.py                    # End-to-end eval demo script
│   ├── docqa_results.md                    # Pre-generated results
│   ├── cache/                              # LLM API response cache (JSON)
│   │   ├── kv_store_llm_response_cache.json
│   │   └── kv_store_multimodel_llm_response_cache.json
│   ├── example_input/
│   │   ├── 2020.acl-main.45.pdf            # Sample academic PDF
│   │   └── 13_qa.jsonl                     # 13 QA pairs with ground truth
│   ├── example_output/
│   │   ├── example_mmkg.graphml            # Built knowledge graph
│   │   ├── example_mmkg_emb.npy            # Precomputed node embeddings
│   │   ├── example_mmkg_report.md          # Build statistics report
│   │   └── retrieval_log.md                # RAG query log
│   ├── example_working/                    # Intermediate build artifacts
│   │   ├── 2020.acl-main.45/auto/         # MinerU parsed output
│   │   ├── images/                         # Extracted images + per-image KGs
│   │   ├── graph_chunk_entity_relation.graphml
│   │   ├── graph_merged_image_*.graphml    # 23 per-image merged graphs
│   │   └── kv_store_*.json                 # 4 KV stores (docs/chunks/images/kg)
│   └── paper/
│       ├── framework.png                   # System architecture diagram
│       └── mmgraphrag.pdf                  # Research paper
│
└── eval_reference/                         # Benchmark evaluation (reference only)
    ├── docbench_eval/                      # DocBench dataset eval scripts
    │   ├── QA.py                           # Main QA driver (229 docs)
    │   ├── evaluate.py                     # LLM-based evaluator
    │   ├── eval_llm.py                     # Eval LLM client
    │   ├── evaluation_prompt.txt           # Eval prompt template
    │   ├── mineru_docbench.py              # MinerU batch preprocessor (implied)
    │   ├── naive_rag.py                    # Naive RAG baseline
    │   ├── check.py                        # Output integrity checker
    │   └── result.py                       # Accuracy aggregator
    └── mmlongbench_eval/                   # MMLongBench dataset eval scripts
        ├── run.py                          # Main eval runner
        ├── eval_score.py                   # ANLS / exact match scorer
        ├── extract_answer.py               # Answer extractor via LLM
        ├── mineru_mmlongbench.py           # MinerU batch preprocessor
        └── prompt_for_answer_extraction.md # Answer extraction prompt
```


---

## 3. Module Descriptions

### 3.1 `main.py` — CLI Entry Point
The top-level argparse-based CLI. Supports three modes:
- **Build mode** (`-i`): calls `MMKGBuilder.index(pdf_path)`
- **Query mode** (`-q`): calls `GraphRAGQuery.query(question, param)`
- **Visualization mode** (`-s`): starts Flask server via `run_visualization_server()`

Handles `parameter.py` overrides via CLI flags (`-w`, `-o`, `-m`, `-f`, `-v`).

---

### 3.2 `src/parameter.py` — Global Configuration
Single source of truth for all runtime parameters:
- LLM API keys, base URLs, model names (text + multimodal)
- Embedding model path and `SentenceTransformer` initialization at import time
- Directory paths (`CACHE_PATH`, `WORKING_DIR`, `OUTPUT_DIR`)
- `QueryParam` dataclass for retrieval tuning
- Processing flags (`USE_MINERU`, `ENTITY_EXTRACT_MAX_GLEANING`, etc.)

> ⚠️ **Concern**: API keys are hardcoded with placeholder strings. The `SentenceTransformer` model loads at import time — any module that imports `parameter` triggers a model load.

---

### 3.3 `src/builder.py` — Pipeline Orchestrator (`MMKGBuilder`)
The main `@dataclass` that wires together all pipeline stages:

| Step | Method | Description |
|------|--------|-------------|
| 1 | `_step_preprocessing` | PDF → text chunks + image data (via MinerU/PyMuPDF) |
| 2 | `_step_text_extraction` | Text chunks → text KG (`.graphml`) |
| 3 | `_step_image_extraction` | Images → per-image KGs |
| 4 | `_step_fusion` | Fuse image KGs into text KG |
| 5 | `_step_save_output` | Copy final `.graphml` to output dir |
| 6 | `_step_generate_report` | Write stats report `.md` |

All steps are idempotent (cache-aware).

---

### 3.4 `src/core/base.py` — Utility Layer
Pure utility functions with no side effects:
- `clean_str`, `split_string_by_multi_markers` — text processing
- `encode_string_by_tiktoken`, `decode_tokens_by_tiktoken` — token counting
- `compute_args_hash`, `compute_mdhash_id` — deterministic hashing for cache keys
- `limit_async_func_call` — semaphore-based async concurrency limiter
- `load_json`, `write_json` — file I/O
- `get_latest_graphml_file` — finds the most recent merged graph in working dir
- `EmbeddingFunc` / `wrap_embedding_func_with_attrs` — embedding wrapper dataclass

---

### 3.5 `src/core/prompt.py` — Prompt Templates (~668 lines)
Contains all `PROMPTS` dict entries:
- Entity/relation extraction prompts (text and image)
- Image description prompt (with/without examples)
- Feature chunk description prompts
- Entity alignment, entity judgement, entity enhancement prompts
- RAG response prompts (base, augmented, multimodal, merge)
- Delimiter constants (`GRAPH_FIELD_SEP`, `TUPLE_DELIMITER`, etc.)

---

### 3.6 `src/core/storage.py` — Storage Abstractions
- `TextChunkSchema` — TypedDict for a text chunk
- `StorageNameSpace` — base dataclass with `index_done_callback()`
- `BaseKVStorage` / `JsonKVStorage` — file-backed key-value store (JSON)
- `BaseGraphStorage` / `NetworkXStorage` — file-backed graph store (GraphML)

`NetworkXStorage` includes graph stabilization utilities adapted from `microsoft/graphrag`.

---

### 3.7 `src/graph/text2graph.py` — Text-to-Graph Pipeline
`TextEntityExtractor` orchestrates LLM-based entity/relation extraction from text chunks:
- Iterative "gleaning" loop for completeness
- Concurrent chunk processing with `asyncio.as_completed`
- Writes per-chunk KG info to `kv_store_chunk_knowledge_graph.json`
- Merges all nodes/edges via `_merge_nodes_then_upsert` / `_merge_edges_then_upsert`

---

### 3.8 `src/graph/img2graph.py` — Image-to-Graph Pipeline
`ImageEntityExtractor` per image:
- `extract_feature_chunks()` — YOLO segmentation to isolate objects
- `feature_image_entity_construction()` — MLLM describes each segment
- `extract_entities_from_image()` — MLLM extracts entities from full image
- `feature_image_relationship_construction()` — MLLM links segments to entities
- Builds a per-image GraphML saved to `working/images/<name>/graph_<name>_entity_relation.graphml`

---

### 3.9 `src/graph/fusion.py` — KG Fusion Pipeline
Most complex module (~550 lines). Bridges image KGs and text KG:
- **Spectral clustering** (`_compute_spectral_labels`) on text entity embeddings
- **Nearest-neighbor classification** assigns image entities to clusters
- **LLM judgment** (`judge_text_entity_alignment_clustering`) merges aligned entities
- **Graph enhancement** (`enhanced_image_knowledge_graph`) enriches image entities with text context
- **Single-image alignment** (`image_knowledge_graph_update`) adds cross-modal edges
- **Graph merge** (`merge_graphs`) fuses image and text graphs using NetworkX compose

---

### 3.10 `src/graph/utils.py` — Shared Graph Helpers
Shared by `text2graph.py` and `img2graph.py`:
- `_handle_single_entity_extraction` — parse entity tuple from LLM output
- `_handle_single_relationship_extraction` — parse relation tuple
- `_handle_entity_relation_summary` — LLM summarizes long entity descriptions
- `_merge_nodes_then_upsert` — deduplicates nodes by majority entity_type
- `_merge_edges_then_upsert` — accumulates edge weights and descriptions

---

### 3.11 `src/llm/client.py` — LLM Client Layer
- Singleton OpenAI client pool (`AsyncOpenAI` + `OpenAI`)
- `model_if_cache` — async text LLM with hash-based KV caching
- `multimodel_if_cache` — async multimodal LLM with caching
- `get_llm_response` / `get_mmllm_response` — sync wrappers for fusion module
- `normalize_to_json` / `normalize_to_json_list` — robust JSON extraction from LLM output

---

### 3.12 `src/preprocessing/pdf_preprocessing.py` — PDF Preprocessing
- `chunking_by_token_size` — tiktoken-based sliding window chunking
- `TextChunking` — stores full docs + text chunks to JSON KV stores
- `PdfChunking` — dual-engine PDF processor:
  - `_process_pymupdf`: uses `fitz`, extracts text + images with context
  - `_process_mineru`: shells out to `mineru` CLI, reads markdown + content_list.json
- `get_image_description` — calls MLLM for image description + YOLO flag
- `compress_image_to_size` — resizes images to stay under API limits

---

### 3.13 `src/retrieval/query.py` — RAG Query Engine (`GraphRAGQuery`)
- Loads graph + pre-built embeddings (or builds them)
- `find_similar_nodes` — cosine similarity over all node embeddings
- `_find_most_related_text_unit_from_entities` — retrieves source text chunks via source_id
- `_find_most_related_edges_from_entities` — retrieves related edges
- `_build_local_query_context` — assembles CSV context for LLM
- `GraphRAGQuery.query()` — 4-stage pipeline: context → text LLM → MLLM augment → merge

---

### 3.14 `src/visualization/server.py` — Visualization Server
Flask app with REST API:
- `GET /` — serves `graph_explorer.html`
- `GET /api/graph/info` — node/edge counts + entity type distribution
- `GET /api/graph/content` — paginated node+edge data
- `GET /api/graph/search` — fuzzy node search
- `GET /api/graph/retrieve` — semantic subgraph highlighting via embeddings

---

### 3.15 `examples/docqa_example.py` — Demo Eval Script
End-to-end pipeline demo:
1. Builds KG from `example_input/2020.acl-main.45.pdf`
2. Answers 13 questions from `13_qa.jsonl`
3. Generates `docqa_results.md` with side-by-side model vs. ground truth

---

### 3.16 `eval_reference/` — Benchmark Scripts (Reference Only)
**Not runnable as-is** — contains hardcoded HPC cluster paths (`/cpfs02/`, `/mnt/workspace/`).

| Sub-module | Purpose |
|------------|---------|
| `docbench_eval/QA.py` | Runs 5 QA methods on 229 DocBench documents |
| `docbench_eval/evaluate.py` | LLM-based answer evaluation |
| `docbench_eval/eval_llm.py` | LLM client for evaluation |
| `docbench_eval/naive_rag.py` | Naive RAG baseline (SentenceTransformer + OpenAI-compatible LLM) |
| `docbench_eval/result.py` | Accuracy computation by type/domain |
| `docbench_eval/check.py` | Detects failed MinerU outputs, reruns them |
| `mmlongbench_eval/run.py` | Runs 5 QA methods on MMLongBench |
| `mmlongbench_eval/eval_score.py` | ANLS + exact match + F1 scoring |
| `mmlongbench_eval/extract_answer.py` | LLM-based answer extraction |
| `mmlongbench_eval/mineru_mmlongbench.py` | Batch MinerU preprocessing |


---

## 4. File Classification

### KEEP — Core Production Code

| File | Role |
|------|------|
| `main.py` | CLI entry point |
| `src/builder.py` | Pipeline orchestrator |
| `src/parameter.py` | Configuration |
| `src/core/base.py` | Utilities |
| `src/core/prompt.py` | Prompt templates |
| `src/core/storage.py` | Storage abstractions |
| `src/core/__init__.py` | Core exports |
| `src/graph/text2graph.py` | Text KG extraction |
| `src/graph/img2graph.py` | Image KG extraction |
| `src/graph/fusion.py` | KG fusion |
| `src/graph/utils.py` | Graph helpers |
| `src/graph/__init__.py` | Graph exports |
| `src/graph/yolov8n-seg.pt` | YOLO weights (required at runtime) |
| `src/llm/client.py` | LLM client |
| `src/llm/__init__.py` | LLM exports |
| `src/preprocessing/pdf_preprocessing.py` | PDF processing |
| `src/preprocessing/__init__.py` | Preprocessing exports |
| `src/retrieval/query.py` | RAG engine |
| `src/retrieval/__init__.py` | Retrieval exports |
| `src/visualization/server.py` | Flask visualization server |
| `src/visualization/graph_explorer.html` | Visualization frontend |
| `src/__init__.py` | Package root |
| `README.md` | Documentation |
| `README_zh.md` | Chinese documentation |
| `LICENSE` | License |

---

### KEEP — Example & Demo Assets

| File | Role |
|------|------|
| `examples/docqa_example.py` | Demo eval script |
| `examples/example_input/2020.acl-main.45.pdf` | Sample document |
| `examples/example_input/13_qa.jsonl` | Sample Q&A dataset |
| `examples/example_output/example_mmkg.graphml` | Pre-built graph |
| `examples/example_output/example_mmkg_emb.npy` | Pre-built embeddings |
| `examples/example_output/example_mmkg_report.md` | Pre-built report |
| `examples/example_output/retrieval_log.md` | Sample retrieval log |
| `examples/paper/framework.png` | Architecture diagram |
| `examples/paper/mmgraphrag.pdf` | Research paper |

---

### MODIFY — Files That Need Changes

| File | Issue | Recommended Change |
|------|-------|--------------------|
| `src/parameter.py` | API keys hardcoded with funny placeholder strings; model loads at import time | Move secrets to `.env` / env vars; lazy-load `EMBED_MODEL` |
| `src/builder.py` | `CACHE_PATH` re-assigned shadowing the import | Remove the local re-assignment on line 23 |
| `src/graph/fusion.py` | Prompt assembled with manual f-string inside `judge_text_entity_alignment_clustering()` instead of using `PROMPTS` dict | Move prompt to `prompt.py` |
| `src/preprocessing/pdf_preprocessing.py` | `filter_keys` logic comment note — inverted condition possible bug | Verify and fix filter logic |
| `src/retrieval/query.py` | Entity type check uses comma-split string scan instead of proper CSV parse | Use `csv.reader` for entities_context parsing |
| `.gitignore` | Only ignores `.DS_Store`; no Python/IDE artifacts ignored | Add `__pycache__/`, `*.pyc`, `.env`, `*.npy`, `cache/`, `working/`, `output/`, `*.graphml` |
| `examples/docqa_results.md` | May contain stale results if code changed | Regenerate or mark as sample output |

---

### REMOVE — Candidates for Removal (after confirmation)

| File | Reason |
|------|--------|
| `examples/example_working/graph_merged_image_*.graphml` (23 files) | Generated intermediate artifacts, not source code; bloat the repo |
| `examples/example_working/kv_store_*.json` | Generated intermediate artifacts |
| `examples/example_working/images/image_*/` (23 folders with graphml) | Generated intermediate artifacts |
| `examples/cache/kv_store_llm_response_cache.json` | Contains cached LLM API responses; potentially stale & large |
| `examples/cache/kv_store_multimodel_llm_response_cache.json` | Same as above |
| `examples/example_working/2020.acl-main.45/auto/` | MinerU intermediate output; reproducible by running the pipeline |

> ✅ `examples/example_output/` files should be **kept** as they are the final demo outputs referenced in documentation.

---

### REMOVE — Eval Reference (after confirmation)

| File | Reason |
|------|--------|
| `eval_reference/docbench_eval/QA.py` | Research-only; hardcoded HPC paths; references old `MMGraphRAG` API |
| `eval_reference/docbench_eval/evaluate.py` | Research-only eval script |
| `eval_reference/docbench_eval/eval_llm.py` | Standalone LLM client duplicating `src/llm/client.py` |
| `eval_reference/docbench_eval/result.py` | Research scoring script |
| `eval_reference/docbench_eval/check.py` | HPC cluster utility |
| `eval_reference/docbench_eval/mineru_docbench.py` | HPC batch preprocessor |
| `eval_reference/mmlongbench_eval/run.py` | Research-only; HPC paths |
| `eval_reference/mmlongbench_eval/extract_answer.py` | Research eval tool |
| `eval_reference/mmlongbench_eval/mineru_mmlongbench.py` | HPC batch preprocessor |

> The README explicitly warns these are reference-only and not runnable. The entire `eval_reference/` folder can be moved to a separate `research/` directory or removed if this is a production deployment.

---

### UNKNOWN — Requires Further Inspection

| File | Question |
|------|----------|
| `src/graph/yolov8n-seg.pt` | Is this the correct model size for the task? The nano model is fastest but least accurate. Should this be configurable? |
| `examples/example_working/2020.acl-main.45/auto/2020.acl-main.45_model.json` | Large MinerU layout detection output — needed for reproducibility? |
| `examples/example_working/images/image_*/` (23 image dirs, each with 3 graphml) | Why are there 3 graphml files per image (`graph_`, `enhanced_graph_`, `new_graph_`)? This is the expected 3-stage fusion output — but should intermediate files be deleted after merge? |
| `examples/docqa_results.md` | Are these results current or from a previous version of the code? |


---

## 5. Detected Code Categories

| Category | Files |
|----------|-------|
| **Graph Construction** | `src/graph/text2graph.py`, `src/graph/img2graph.py`, `src/graph/fusion.py`, `src/graph/utils.py` |
| **Multimodal Processing** | `src/graph/img2graph.py`, `src/preprocessing/pdf_preprocessing.py`, `src/retrieval/query.py` |
| **Retrieval / RAG** | `src/retrieval/query.py`, `src/builder.py` |
| **Model Loading** | `src/parameter.py` (SentenceTransformer), `src/graph/img2graph.py` (YOLO) |
| **Inference Pipeline** | `src/builder.py`, `main.py` |
| **LLM Interaction** | `src/llm/client.py`, `src/core/prompt.py` |
| **Preprocessing** | `src/preprocessing/pdf_preprocessing.py` |
| **Visualization** | `src/visualization/server.py`, `src/visualization/graph_explorer.html` |
| **Benchmark/Eval Code** | `eval_reference/docbench_eval/*`, `eval_reference/mmlongbench_eval/*` |
| **Demo Code** | `examples/docqa_example.py` |
| **Research-Only Code** | All of `eval_reference/` |
| **Configuration** | `src/parameter.py` |
| **Storage Abstractions** | `src/core/storage.py` |
| **Utilities** | `src/core/base.py` |

---

## 6. Dependency Discovery

### Method 1: README-documented dependencies

From `README.md` "Dependencies Installation" section:

```
openai
sentence-transformers
networkx
numpy
scikit-learn
Pillow
tqdm
tiktoken
ultralytics
opencv-python
flask
flask-cors
pymupdf  (optional, at least one PDF parser required)
mineru[all]  (optional, at least one PDF parser required)
```

### Method 2: Import statement scanning (all Python files)

#### `src/core/base.py`
```python
import asyncio, html, json, logging, os, re, hashlib
import numpy
import tiktoken
```

#### `src/core/storage.py`
```python
import html, os
import networkx
from graspologic.utils  # used in NetworkXStorage.stable_largest_connected_component()
```

#### `src/llm/client.py`
```python
import ast, json, re
import numpy
from openai import AsyncOpenAI, OpenAI
```

#### `src/graph/text2graph.py`
```python
import asyncio, json, os, re
from tqdm import tqdm
```

#### `src/graph/img2graph.py`
```python
import asyncio, base64, os, shutil, re
import cv2
import numpy
from PIL import Image
from tqdm import tqdm
from ultralytics import YOLO
```

#### `src/graph/fusion.py`
```python
import math, os, base64
import xml.etree.ElementTree
import networkx
import numpy
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from tqdm import tqdm
```
> Note: `NearestNeighbors` is imported but the implementation was replaced by a manual nearest-neighbor search.

#### `src/preprocessing/pdf_preprocessing.py`
```python
import asyncio, base64, json, os, re, shutil, subprocess
from io import BytesIO
from PIL import Image
from tqdm import tqdm
# conditional: import fitz  (PyMuPDF)
```

#### `src/retrieval/query.py`
```python
import asyncio, base64, json, os, re
import networkx
import numpy
from sklearn.metrics.pairwise import cosine_similarity
```

#### `src/visualization/server.py`
```python
import json, os, xml.etree.ElementTree
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
```

#### `src/parameter.py`
```python
from sentence_transformers import SentenceTransformer
```

#### `examples/docqa_example.py`
```python
import asyncio, json, logging, os, sys
# all others from src/
```

#### `eval_reference/docbench_eval/QA.py`
```python
import fitz          # PyMuPDF
import torch
from PIL import Image
from transformers import AutoModelForCausalLM
# references mmgraphrag (old API)
```

#### `eval_reference/docbench_eval/eval_llm.py`
```python
from openai import OpenAI
import torch
from PIL import Image
```

#### `eval_reference/docbench_eval/naive_rag.py`
```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy
from openai import OpenAI
```

#### `eval_reference/mmlongbench_eval/run.py`
```python
import fitz, torch, numpy
from openai import OpenAI
from PIL import Image
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoModelForCausalLM
```

#### `eval_reference/mmlongbench_eval/extract_answer.py`
```python
from openai import OpenAI
```


---

## 7. Generated requirements.txt

The following `requirements.txt` was synthesized from all discovered imports. It covers the **core production codebase** (`src/`) with pinning recommendations based on current stable versions.

```
# =====================================================
# MMGraphRAG — Generated requirements.txt
# Core production dependencies (src/)
# Generated: August 1, 2026 by repository audit
# =====================================================

# LLM API client
openai>=1.30.0

# Text embeddings (local model)
sentence-transformers>=3.0.0

# Knowledge graph storage and manipulation
networkx>=3.3

# YOLO-based image segmentation
ultralytics>=8.2.0

# Image processing
opencv-python>=4.9.0.80
Pillow>=10.3.0

# Numerical computing
numpy>=1.26.4

# Machine learning utilities
scikit-learn>=1.4.2

# Graph connected-components utility (used in NetworkXStorage.stable_largest_connected_component)
graspologic>=3.3.0

# Token counting for text chunking
tiktoken>=0.7.0

# Progress bars
tqdm>=4.66.4

# Web visualization server
flask>=3.0.3
flask-cors>=4.0.1

# PDF parsing (choose at least one)
# Option A: MinerU (recommended, install separately per official docs)
# mineru[all]>=1.0.0

# Option B: PyMuPDF (lightweight fallback)
pymupdf>=1.24.5
```

Save this as `requirements.txt` in the project root:

```bash
pip install -r requirements.txt
```

### Optional: eval_reference extra dependencies

```
# eval_reference/ only — NOT required for core operation
torch>=2.3.0
transformers>=4.41.0
```


---

## 8. Missing Dependencies

### Critical Missing

| Package | Where Needed | Status |
|---------|-------------|--------|
| `graspologic` | `src/core/storage.py` — `NetworkXStorage.stable_largest_connected_component()` calls `graspologic.utils.largest_connected_component` | **Not in README** — will `ImportError` at runtime if that method is called |

> However, `stable_largest_connected_component` appears to be unused in the current codebase (it's a static method with no callers found). It was likely carried over from `nano-graphrag`. Still needs to be declared if the method is retained.

### Conditional Missing (PDF Parsing)

| Package | Status |
|---------|--------|
| `pymupdf` (PyMuPDF / `fitz`) | Listed in README as optional, but **no requirements file exists** — users may miss installing it |
| `mineru` | External CLI tool; setup is non-trivial (requires model downloads). README documents this but there's no automated check beyond `shutil.which('mineru')` |

### Possible Missing (Eval Scripts Only)

| Package | Where Needed |
|---------|-------------|
| `torch` | `eval_reference/docbench_eval/eval_llm.py`, `eval_reference/mmlongbench_eval/run.py` |
| `transformers` | `eval_reference/docbench_eval/QA.py` (for `AutoModelForCausalLM` / Ovis model) |

These are only needed to reproduce the paper's benchmark experiments, not for the core pipeline.

### Unused Imports Detected

| File | Import | Status |
|------|--------|--------|
| `src/graph/fusion.py` | `from sklearn.neighbors import NearestNeighbors` | Imported but replaced by manual numpy dot product. Can be removed. |
| `src/graph/text2graph.py` | `PROCESS_TICKERS` from `PROMPTS` | Defined and imported but never used in the file. |
| `src/graph/fusion.py` | `from sklearn.cluster import DBSCAN` (used via sklearn) | Actually used; fine. |

---

## 9. Cleanup Recommendations

### Priority 1 — Security (Do First)

1. **Remove hardcoded API keys** from `src/parameter.py`. Replace with `os.environ.get()`:
   ```python
   API_KEY = os.environ.get("LLM_API_KEY", "")
   MM_API_KEY = os.environ.get("MM_API_KEY", "")
   ```
2. **Add `.env` support** via `python-dotenv` and add `.env` to `.gitignore`.
3. **Expand `.gitignore`** to prevent accidental commits of:
   - `__pycache__/`, `*.pyc`, `*.pyo`
   - `.env`, `*.env`
   - `working/`, `output/`, `cache/`  (generated artifacts)
   - `models/`  (embedding model weights)
   - `*.npy`, `*.graphml` (large generated files)

### Priority 2 — Correctness

4. **Fix the `filter_keys` logic** in `src/preprocessing/pdf_preprocessing.py` (`TextChunking.text_chunking`):
   The comment notes that `filter_keys` returns keys **not** in storage, but the variable is assigned to `{k for k in data if k in existing_doc_keys}` — this will insert nothing if `filter_keys` returns missing keys correctly. Verify the logic and rename variables for clarity.

5. **Remove unused import** `NearestNeighbors` from `src/graph/fusion.py`.

6. **Fix shadow variable** in `src/builder.py` line ~23: `CACHE_PATH = parameter.CACHE_PATH or "cache"` shadows the imported `CACHE_PATH` from `parameter`. Use a different variable name or remove it entirely.

### Priority 3 — Dependency Management

7. **Add `requirements.txt`** to the repo (see Section 7).
8. **Add `pyproject.toml`** with `[project]` metadata for proper packaging.
9. **Declare `graspologic`** as a dependency, or remove `stable_largest_connected_component` if unused.

### Priority 4 — Code Quality

10. **Lazy-load the embedding model** in `parameter.py`:
    ```python
    _EMBED_MODEL = None
    def get_embed_model():
        global _EMBED_MODEL
        if _EMBED_MODEL is None:
            _EMBED_MODEL = SentenceTransformer(EMBEDDING_MODEL_DIR, device="cpu")
        return _EMBED_MODEL
    ```
    This prevents the model from loading during import for tests or CLI help.

11. **Move the inline prompt** in `fusion.judge_text_entity_alignment_clustering()` to `PROMPTS` in `prompt.py` to keep all prompts in one place.

12. **Intermediate KG cleanup**: The 3-stage fusion creates `graph_`, `enhanced_graph_`, and `new_graph_` files per image. Consider deleting intermediate stages after the final merge to avoid working directory bloat.

13. **Add a `models/` directory** with a `.gitkeep` and a `README.md` explaining how to download `all-MiniLM-L6-v2`.

### Priority 5 — Repository Hygiene

14. **Remove generated intermediate files** from `examples/example_working/`:
    - 23 `graph_merged_image_*.graphml` files
    - `kv_store_*.json` files
    - Per-image sub-directories with graphml files
    - MinerU intermediate output in `2020.acl-main.45/auto/`
    These are reproducible outputs and bloat the repository unnecessarily.

15. **Consider archiving `eval_reference/`** to a separate branch or moving to a `research/` top-level directory with a clear warning that these are not runnable without HPC infrastructure.

---

## 10. Suggested Architecture Improvements

### 10.1 Configuration Management
Currently all config lives in `parameter.py` as module-level globals. This makes testing difficult (can't swap configs between tests) and mixes secrets with hyperparameters.

**Recommendation**: Adopt a typed config class with environment variable loading:
```
src/config.py       ← Pydantic BaseSettings or dataclass
.env                ← API keys, model paths
.env.example        ← Committed template
```

---

### 10.2 LLM Provider Abstraction
`client.py` is tightly coupled to the OpenAI API format (DashScope's compatible mode). If users want to swap providers, they must edit `client.py` and `parameter.py`.

**Recommendation**: Add a thin provider abstraction:
```
src/llm/
  base.py          ← Protocol/ABC: LLMProvider
  openai_provider.py
  client.py        ← factory function: get_provider(config)
```

---

### 10.3 Pipeline Observability
The pipeline writes logs to stdout but has no structured progress tracking or failure recovery beyond the "skip if file exists" cache checks. A failed fusion run leaves partial state with no clear resumption point.

**Recommendation**:
- Add a `pipeline_state.json` that tracks which steps completed with timestamps
- Make each step idempotent via state file (currently only file-existence checks)
- Add structured logging with JSON format option

---

### 10.4 Embedding Rebuild
`GraphRAGQuery` builds embeddings once and caches them as `.npy`. If the graph is updated, embeddings go stale silently.

**Recommendation**: Store a hash of the source graphml file alongside the `.npy`. On load, validate hash and trigger rebuild if mismatched.

---

### 10.5 Async/Sync Boundary
The `fusion.py` module uses synchronous `get_llm_response()` and `get_mmllm_response()` while `text2graph.py` and `img2graph.py` use `async/await`. This inconsistency means fusion blocks the event loop.

**Recommendation**: Convert `fusion.py` to use `await model_if_cache()` throughout and run inside the existing async context in `builder.py`.

---

### 10.6 YOLO Model Configuration
`yolov8n-seg.pt` (nano model) is bundled directly in `src/graph/`. It:
- Adds ~6MB binary to the repository
- Cannot be easily swapped for a larger model
- Always runs on CPU

**Recommendation**:
- Move to `models/yolo/` and reference via `parameter.py`
- Make configurable: `YOLO_MODEL_PATH`, `YOLO_DEVICE`
- Add download script or model card

---

### 10.7 Decoupling `parameter.py` from `EMBED_MODEL`
The global `EMBED_MODEL` is instantiated at module import time. Any file that does `from .. import parameter` triggers a full model load (~100ms+ even cached). This slows down CLI startup and breaks unit testing.

**Recommendation**: Lazy initialization pattern (see Section 9 item 10).

---

### 10.8 Prompt Versioning
All prompts are in a single `PROMPTS` dict with no versioning. A prompt change silently invalidates all cached responses.

**Recommendation**: Include a `PROMPTS_VERSION` string that is hashed into cache keys alongside model name.

---

*End of Repository Audit Report*

---

> **Action Required**: Review the above findings and approve before any modifications are made to the codebase. Items in Section 9 are prioritized in order of risk and impact.
