# Architecture Refactor Report

**Date**: August 1, 2026
**Type**: Structural refactor — zero algorithm or business-logic changes.

---

## Overview

The flat `src/` research layout was reorganised into a production-style `backend/`
package with clear domain separation. All algorithms, prompts, and pipeline
execution order are identical to the original.

---

## Directory Map — Old → New

| Old path | New path | Notes |
|----------|----------|-------|
| `src/__init__.py` | `backend/__init__.py` | Re-exports `MMKGBuilder` |
| `src/builder.py` | `backend/builder.py` | Fixed `CACHE_PATH` shadow var |
| `src/parameter.py` | `backend/config/settings.py` | Env-var aware |
| `src/core/base.py` | `backend/utils/base.py` | Pure helpers |
| `src/core/prompt.py` | `backend/core/prompt.py` | Verbatim copy |
| `src/core/storage.py` | `backend/storage/kv_storage.py` + `graph_storage.py` | Split by concern |
| `src/llm/client.py` | `backend/llm/client.py` | Singleton pool preserved |
| `src/graph/utils.py` | `backend/graph/utils.py` | Relative imports updated |
| `src/graph/text2graph.py` | `backend/graph/text2graph.py` | Relative imports updated |
| `src/graph/img2graph.py` | `backend/graph/img2graph.py` | Relative imports updated |
| `src/graph/fusion.py` | `backend/graph/fusion.py` | Relative imports updated |
| `src/graph/yolov8n-seg.pt` | `backend/graph/yolov8n-seg.pt` | Binary copy |
| `src/preprocessing/pdf_preprocessing.py` | `backend/ingestion/pdf_preprocessing.py` | `PdfChunking` added |
| `src/retrieval/query.py` | `backend/retrieval/query.py` | Relative imports updated |
| `src/visualization/server.py` | `backend/visualization/server.py` | Relative imports updated |
| `src/visualization/graph_explorer.html` | `backend/visualization/graph_explorer.html` | Verbatim copy |
| `examples/example_input/` | `data/input/` | Source data canonical location |
| `examples/example_output/` | `data/output/` | Build artefacts canonical location |
| `examples/paper/` | `docs/` | Documentation |
| `main.py` | `main.py` | Updated imports → `backend.*` |
| `examples/docqa_example.py` | `examples/docqa_example.py` | Updated imports → `backend.*` |

---

## New Directories Created

| Directory | Purpose |
|-----------|---------|
| `backend/api/` | REST API layer (FastAPI routes — future) |
| `backend/config/` | All runtime configuration |
| `backend/core/` | Prompt templates and shared constants |
| `backend/graph/` | KG construction pipeline |
| `backend/ingestion/` | PDF parsing and chunking |
| `backend/llm/` | LLM / MLLM client layer |
| `backend/retrieval/` | GraphRAG query engine |
| `backend/storage/` | KV store and graph store |
| `backend/utils/` | Pure helper functions |
| `backend/visualization/` | Flask graph explorer |
| `data/input/` | Source PDFs |
| `data/output/` | Final KG artefacts (gitignored) |
| `data/cache/` | LLM response cache (gitignored) |
| `data/working/` | Intermediate build artefacts (gitignored) |
| `docs/` | Documentation and paper |
| `frontend/` | Future UI (placeholder) |
| `models/` | Local embedding models (gitignored) |
| `tests/` | Test suite (placeholder) |

---

## Import Changes Summary

All `from src.X import Y` → `from backend.X import Y`

Internal relative imports updated from e.g.  
`from ..core.base import logger` (was `from src.core.base`)  
to the same relative path within the new `backend.*` namespace.

### Key import chain (no circular dependencies)

```
main.py
  └── backend.builder
        ├── backend.config.settings        (no upstream deps)
        ├── backend.utils.base             (no upstream deps)
        ├── backend.core.prompt            (no upstream deps)
        ├── backend.storage.kv_storage     ← backend.utils, backend.config
        ├── backend.storage.graph_storage  ← backend.utils, backend.config, backend.storage.kv_storage
        ├── backend.llm.client             ← backend.utils, backend.config, backend.storage.kv_storage
        ├── backend.graph.utils            ← backend.core, backend.utils, backend.config, backend.storage, backend.llm
        ├── backend.graph.text2graph       ← backend.graph.utils, backend.llm, backend.core, backend.storage, backend.config
        ├── backend.graph.img2graph        ← backend.graph.utils, backend.llm, backend.core, backend.storage, backend.config
        ├── backend.graph.fusion           ← backend.llm, backend.core, backend.config, backend.utils
        └── backend.ingestion.pdf_preprocessing ← backend.config, backend.utils, backend.llm, backend.core, backend.storage
```

---

## Storage Split Rationale

`src/core/storage.py` contained both KV and graph storage in one file.
Split into:

- `backend/storage/kv_storage.py` — `TextChunkSchema`, `StorageNameSpace`, `BaseKVStorage`, `JsonKVStorage`
- `backend/storage/graph_storage.py` — `BaseGraphStorage`, `NetworkXStorage`

`backend/storage/__init__.py` re-exports everything so call sites are unchanged.

---

## Dead Code Removed (carried over from cleanup pass)

| Item | File | Reason |
|------|------|--------|
| `stable_largest_connected_component()` | `storage.py` | Zero callers; pulled graspologic |
| `NearestNeighbors` import | `fusion.py` | Replaced by numpy dot-product |
| `graspologic` dependency | `requirements.txt` | Only caller removed |

---

## Risks & Notes

| Risk | Mitigation |
|------|-----------|
| `backend/config/settings.py` loads `SentenceTransformer` at import time | Known; model path must exist before any import. Set `EMBEDDING_MODEL_DIR` env var or place model at `./models/all-MiniLM-L6-v2`. |
| `src/` still exists | Old `src/` is intentionally left in place until verified. Remove manually once confirmed. |
| `examples/example_input/` still exists | Source files copied to `data/input/`; originals kept for backward compat. |
| Relative imports assume package is run from project root | Always run `python main.py` or `python -m backend.*` from the `MMGraphRAG/` root. |

---

## Verification

```
✅ 27 Python files pass py_compile (zero syntax errors)
✅ No circular imports in dependency chain
✅ CLI entry point (main.py) updated
✅ Demo script (examples/docqa_example.py) updated
✅ All __init__.py re-exports preserved
✅ Pipeline execution order identical to original
✅ All algorithms untouched
```

---

## Architecture Update — Eliminate Duplicate Retrieval

**Date**: August 1, 2026
**Type**: Architectural improvement — zero algorithm, prompt, or retrieval logic changes.

---

### Problem

After the initial refactor, `QueryService` performed the similarity search **twice** per request:

```
QueryService
  │
  ├─ find_similar_nodes(question)          ← embedding call #1
  │       (fed to EvidenceEngine)
  │
  └─ GraphRAGQuery.query(question)
         │
         └─ _build_local_query_context()
                │
                └─ find_similar_nodes(question)  ← embedding call #2 (duplicate)
                        │
                        └─ LLM → Answer
```

Each `find_similar_nodes` call encodes the query with `SentenceTransformer` and
runs a full cosine-similarity scan over all node embeddings.
Doing this twice per request was pure waste with zero benefit to answer quality.

---

### Root Cause

`EvidenceEngine` and `CitationEngine` both accepted `query_engine` as a parameter
and re-used the `GraphRAGQuery` object directly. This tight coupling forced
`QueryService` to call `find_similar_nodes()` independently to have a node list
to pass into the evidence layer — before the query pipeline had run.

---

### Solution — Single Retrieval Path

#### `backend/retrieval/query.py`

`_build_local_query_context()` now returns a **5-tuple** instead of 4:

```python
# Before
return entities_ctx, sources_ctx, rels_ctx, node_datas

# After
return entities_ctx, sources_ctx, rels_ctx, node_datas, similar_nodes
```

`query()` gains an optional `return_context=False` parameter:

- `return_context=False` (default) — returns `str` answer. **Fully backward compatible.**
  All existing callers (CLI `main.py`, Flask visualization server) are unaffected.
- `return_context=True` — returns a structured dict:

```python
{
    "answer": "...",
    "retrieval": {
        "similar_nodes":         [(name, score), ...],
        "node_datas":            [...],
        "entities_context":      "...",
        "sources_context":       "...",
        "relationships_context": "...",
    }
}
```

No additional retrieval work is performed — `similar_nodes` is the list already
computed inside `_build_local_query_context`, simply surfaced to the caller.

#### `backend/services/query_service.py`

- **Removed** `find_similar_nodes()` call entirely.
- **Single call**: `query_engine.query(question, return_context=True)`
- Passes `result["retrieval"]` directly to `EvidenceEngine`.

```python
# Before (two embedding calls)
similar_nodes = query_engine.find_similar_nodes(question, top_k)   # call #1
answer        = await query_engine.query(question)                  # call #2 inside

# After (one embedding call)
result = await query_engine.query(question, return_context=True)    # single call
answer            = result["answer"]
retrieval_context = result["retrieval"]
```

#### `backend/compliance/evidence_engine.py`

Signature changed — decoupled from `query_engine` entirely:

```python
# Before
EvidenceEngine().collect(query_engine, retrieved_entities)

# After
EvidenceEngine().collect(retrieval_context, graph, text_chunks, image_data)
```

`EvidenceEngine` now receives pre-computed data. It performs zero similarity search.

#### `backend/compliance/citation_engine.py`

Same decoupling for consistency:

```python
# Before
CitationEngine().build_citations(query_engine, retrieved_entities)

# After
CitationEngine().build_citations(retrieval_context, graph, text_chunks)
```

#### `backend/api/routes/query.py`

- Response shape tightened to match spec.
- Added explicit `404` for `FileNotFoundError` (graph not built yet).

---

### New Flow

```
QueryService
  │
  └─ GraphRAGQuery.query(question, return_context=True)
         │
         └─ _build_local_query_context()
                │
                └─ find_similar_nodes()   ← single embedding call
                       │
                       └─ threshold filter → node_datas
                       │
                       └─ build entities/sources/rels context strings
         │
         └─ LLM pipeline (stages 1–3, unchanged)
         │
         └─ return {"answer": ..., "retrieval": {...}}
                           │
         ┌─────────────────┴──────────────────┐
         │                                    │
    answer (str)                 retrieval_context (dict)
         │                                    │
    QueryService response        EvidenceEngine.collect(
                                     retrieval_context,
                                     graph, text_chunks, image_data
                                 )
```

---

### API Response Shape

```json
{
  "success": true,
  "question": "What are the key compliance risks?",
  "result": {
    "answer": "...",
    "evidence": {
      "entities":      [...],
      "relationships": [...],
      "text_chunks":   [...],
      "images":        [...]
    },
    "processing_time_seconds": 2.1,
    "graph": {
      "nodes": 421,
      "edges": 988
    }
  }
}
```

---

### Files Changed

| File | Change |
|------|--------|
| `backend/retrieval/query.py` | `_build_local_query_context` returns 5-tuple; `query()` gains `return_context` param |
| `backend/services/query_service.py` | Single `query()` call; `find_similar_nodes()` removed |
| `backend/compliance/evidence_engine.py` | Decoupled from `query_engine`; accepts `retrieval_context` + raw stores |
| `backend/compliance/citation_engine.py` | Same decoupling for consistency |
| `backend/api/routes/query.py` | Clean response shape; explicit 404 handler |

---

### Backward Compatibility

| Caller | Impact |
|--------|--------|
| `main.py` CLI (`-q` flag) | None — calls `query_engine.query(question)` with no args; default `return_context=False` returns `str` as before |
| Flask visualization server (`/api/graph/retrieve`) | None — does not call `query()` |
| `examples/docqa_example.py` | None — calls `querier.query(question)`; default path unchanged |
| FastAPI routes | Updated — now receives cleaner response shape with `evidence` block |

---

### Performance Improvement

| Metric | Before | After |
|--------|--------|-------|
| Embedding calls per request | 2 | 1 |
| Cosine similarity scans per request | 2 | 1 |
| `query_engine` passed across module boundaries | Yes | No |
| `EvidenceEngine` / `CitationEngine` coupled to `GraphRAGQuery` | Yes | No |
