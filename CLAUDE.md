# TEST-INOVA — Claude Code Instructions

## Context Navigation (ALWAYS FOLLOW THIS)

When you need to understand the codebase, locate a function, or trace a flow:

1. **ALWAYS query the knowledge graph first**: `/graphify query "your question"`
2. **To explain a specific symbol**: `/graphify explain "SymbolName"`
3. **To trace how two things connect**: `/graphify path "SourceA" "TargetB"`
4. **Browse structure**: open `graphify-out/GRAPH_REPORT.md` as your navigation entrypoint
5. **Only read raw files** if I explicitly say "read the file" or "show me the raw file"

> The graph is at `graphify-out/graph.json` — 1525 nodes, 3092 edges, 91 communities.
> If code has changed since the graph was built, run: `graphify update .`

---

## Project Overview

Full-stack AI-powered application with:
- **Backend**: Python / FastAPI (`backend/`)
- **Frontend**: React / TypeScript (`frontend/src/`)
- **Auth**: Supabase-based JWT auth + RBAC (`backend/auth/`)
- **Storage**: CockroachDB vector + graph storage (`backend/cockroach_*.py`)
- **Knowledge Graph**: NanoGraphRAG-style pipeline (`backend/graph/`, `src/graph/`)
- **API Routes**: FastAPI routes for upload, query, report, cases, workspace (`backend/api/routes/`)

## Key Architecture Hubs (from graph analysis)

| Hub | Role |
|-----|------|
| `workspace_service.py` | Central workspace management |
| `auth.py` | Authentication entry point |
| `backend/graph/fusion.py` | Graph fusion logic |
| `CockroachGraphStorage` | Primary graph storage class |
| `cockroach_vector_storage.py` | Vector search layer |
| `query_service.py` | Query orchestration |
| `backend/builder.py` | Pipeline builder |
| `AuthContext` / `AuthContext.tsx` | Frontend auth state |
| `App.tsx` | Frontend root |
| `dependencies` | FastAPI dependency injection |

## Stack

- **Python 3.14**, FastAPI, Supabase (auth + DB), CockroachDB
- **React + TypeScript**, Vite, Tailwind CSS
- **Tree-sitter AST** parsed graph (local, no LLM needed for code)

## Graphify Commands Reference

```bash
# Rebuild after code changes (incremental, fast)
graphify update .

# Query the graph
graphify query "how does authentication work"
graphify explain "WorkspaceService"
graphify path "upload route" "CockroachGraphStorage"

# Full rebuild
graphify . --code-only

# With SQL schemas (after pip install "graphifyy[sql]")
graphify . --code-only
```

## File Layout

```
TEST-INOVA/
├── backend/
│   ├── api/routes/          # FastAPI route handlers
│   ├── auth/                # Auth, RBAC, Supabase client, migrations
│   │   ├── services/        # Business logic (auth, workspace, case, profile)
│   │   ├── routes/          # Auth API endpoints
│   │   ├── rbac/            # Role-based access control
│   │   └── migrations/      # SQL migration files
│   ├── graph/               # Graph extraction (text2graph, img2graph, fusion)
│   ├── retrieval/           # Query & retrieval logic
│   ├── compliance/          # Citation + evidence engines
│   ├── config/              # App settings
│   ├── cockroach_graph_storage.py
│   └── cockroach_vector_storage.py
├── frontend/src/            # React/TypeScript UI
├── src/                     # Shared graph/retrieval modules
├── graphify-out/            # Knowledge graph output (DO NOT edit manually)
│   ├── graph.json           # Full graph — query this, not raw files
│   ├── GRAPH_REPORT.md      # Community hubs and navigation guide
│   └── graph.html           # Interactive visual graph (open in browser)
└── CLAUDE.md                # This file
```
