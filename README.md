# Enterprise Compliance Intelligence Platform

**A Multi-Modal Knowledge Graph RAG Framework for Enterprise Compliance**

An end-to-end platform that transforms heterogeneous enterprise documents — PDFs, Word documents, Excel spreadsheets, audio recordings, and images — into unified multi-modal knowledge graphs. Powered by GraphRAG retrieval, evidence scoring, citation verification, workspace multi-tenancy, and an interactive React 19 web dashboard.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture & Workflow](#architecture--workflow)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Environment Configuration](#environment-configuration)
- [Installation & Setup](#installation--setup)
- [Usage Instructions](#usage-instructions)
  - [Full-Stack Web Application](#1-running-the-full-stack-web-application)
  - [CLI Commands](#2-cli-usage)
  - [Flask Graph Explorer](#3-standalone-visualization-server)
  - [Docker Container](#4-docker-deployment)
  - [Evaluation & Benchmarks](#5-evaluation--benchmarks)
- [REST API Reference](#rest-api-reference)
- [License](#license)

---

## Key Features

- **Multi-Modal Document Ingestion**: Supports PDF, DOCX, XLSX, MP3/WAV audio (via OpenAI Whisper), images (PNG/JPG), and plain text.
- **Dual PDF Extraction Engine**: Layout-aware parsing via MinerU with an automatic fallback to PyMuPDF (`fitz`).
- **Visual Entity & Scene Graph Processing**: Extracts visual entities and scene graphs from document figures, charts, and diagrams using GPT-4o Vision (with Pillow for image preprocessing).
- **Spectral Clustering Graph Fusion**: Merges text knowledge graphs and visual scene graphs into a unified Multi-Modal Knowledge Graph (MMKG) using DBSCAN and cosine similarity.
- **GraphRAG & Explainable AI Retrieval**: Entity-level vector similarity search using `sentence-transformers/all-MiniLM-L6-v2`, local/global graph context retrieval, evidence confidence scoring, citation linking, and automated compliance reporting.
- **Workspace Multi-Tenancy & RBAC**: Tenant isolation with workspace-scoped data processing, Supabase Auth integration, JWT verification via JWKS, Role-Based Access Control (RBAC), and audit logging.
- **Modern Web Dashboard**: Built with React 19, TypeScript, Vite, Tailwind CSS, and `@xyflow/react` for interactive force-directed graph exploration, workspace switching, compliance case management, and evidence viewing.
- **Production-Ready & Containerized**: Dockerized setup (Python 3.12-slim), Render backend configuration (`render.yaml`), and Vercel frontend support.

---

## Architecture & Workflow

```
                        [ Document Ingestion Layer ]
         PDF / DOCX / XLSX / Audio (Whisper) / Images (PNG/JPG)
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            Text Processing                 Visual Processing
       (MinerU / PyMuPDF Chunking)       (GPT-4o Vision + Pillow)
                    │                               │
                    ▼                               ▼
           Text Knowledge Graph            Visual Scene Graph
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
                     [ Multi-Modal Graph Fusion ]
                (Spectral Clustering: DBSCAN + Embeddings)
                                    │
                                    ▼
                      Unified Multi-Modal KG (MMKG)
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
[ Workspace & Auth Storage ]                       [ GraphRAG Retrieval ]
  (Supabase Auth + NetworkX)                   (Vector Search + Context RAG)
           │                                                 │
           └────────────────────────┬────────────────────────┘
                                    ▼
                       [ Interactive Web Dashboard ]
                      (React 19 + @xyflow/react UI)
```

1. **Ingestion**: Documents are parsed by specialized extractors (MinerU/PyMuPDF for PDFs, `python-docx` for Word, `openpyxl` for Excel, OpenAI Whisper for audio).
2. **Entity & Relation Extraction**: Text LLM extracts structured entities and relations; visual pipelines perform GPT-4o vision scene graph extraction.
3. **Graph Fusion**: Text and image graph representations are aligned and merged via spectral clustering (DBSCAN over node embedding matrices).
4. **Retrieval & Evidence**: Queries retrieve top-k vector-matched entities and local graph neighborhoods, feeding an evidence scoring engine and citation tracker to produce explainable compliance responses.
5. **Security & Workspace Isolation**: All document uploads, knowledge graph builds, queries, and reports are partitioned by workspace ID and guarded by JWT middleware.

---

## Technology Stack

### Backend
- **Framework**: Python 3.11+, FastAPI (ASGI), Uvicorn, Flask (standalone visualization)
- **AI / LLM / MLLM**: OpenAI API (`gpt-4o` for text, vision, and Whisper audio transcription)
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`), PyTorch, HuggingFace
- **Image & Vision**: Pillow (`PIL`) for image loading, resizing, and base64 encoding; OpenAI `gpt-4o` Vision for visual entity & scene graph extraction *(Note: YOLOv8 and OpenCV were used in legacy research code under `src/` but have been replaced by direct GPT-4o vision prompting in `backend/`)*
- **Graph & Math**: NetworkX, Tiktoken, scikit-learn, NumPy
- **PDF & Document Parsing**: MinerU (`mineru[all]`), PyMuPDF (`pymupdf`), `python-docx`, `openpyxl`
- **Auth & Database**: Supabase (`supabase`), PyJWT (`python-jose`), `email-validator`

### Frontend
- **Framework**: React 19, TypeScript, Vite 6
- **Styling**: Tailwind CSS 4, `@tailwindcss/vite`, PostCSS, Lucide React
- **Graph Visualization**: `@xyflow/react` (React Flow 12)
- **State & Animation**: Framer Motion, Class Variance Authority (`cva`), `clsx`, `tailwind-merge`
- **Authentication**: `@supabase/supabase-js`, custom workspace guards & token store

### Infrastructure & Tools
- **Containerization**: Docker (`Python 3.12-slim`)
- **Deployment Manifests**: Render (`render.yaml`), Vercel (`frontend/vercel.json`)
- **Code Quality**: Ruff (`pyproject.toml`), Vitest, ESLint

---

## Project Structure

```
InnovaHack/
├── backend/                        # Backend REST API & Knowledge Graph Engine
│   ├── api/                        # REST API Routing Layer
│   │   ├── routes/                 # FastAPI Route Modules
│   │   │   ├── cases.py            # Compliance case & workflow endpoints
│   │   │   ├── graph.py            # Standalone/CLI graph endpoint
│   │   │   ├── query.py            # Legacy query endpoint
│   │   │   ├── report.py           # Legacy report endpoint
│   │   │   ├── storage.py          # Graph/KV storage status endpoints
│   │   │   ├── upload.py           # Legacy upload endpoint
│   │   │   ├── workspace_graph.py  # Workspace-scoped graph endpoints
│   │   │   ├── workspace_query.py  # Workspace-scoped RAG query endpoints
│   │   │   ├── workspace_report.py # Workspace-scoped compliance reporting
│   │   │   └── workspace_upload.py # Workspace-scoped multi-format document ingestion
│   │   └── main.py                 # FastAPI application entry point & CORS configuration
│   ├── auth/                       # Authentication & Multi-Tenancy Module
│   │   ├── middleware/             # JWT authentication middleware
│   │   ├── migrations/             # Database migration scripts
│   │   ├── models/                 # User & workspace Pydantic models
│   │   ├── rbac/                   # Role-Based Access Control logic
│   │   ├── routes/                 # Auth, profile, workspace, and audit log routes
│   │   ├── services/               # Supabase auth & workspace services
│   │   ├── dependencies.py         # FastAPI auth dependencies
│   │   ├── supabase_client.py      # Supabase client initialization
│   │   └── workspace.py            # Workspace context helper utilities
│   ├── compliance/                 # Compliance Audit & Evidence Engine
│   │   ├── citation_engine.py      # Source document citation generator
│   │   └── evidence_engine.py      # Confidence scoring & evidence verification
│   ├── config/                     # Configuration Management
│   │   └── settings.py             # Runtime settings, env variables, & lazy embedding loader
│   ├── core/                       # Core Prompts & Constants
│   │   └── prompt.py               # Prompt templates for LLM entity extraction & RAG
│   ├── graph/                      # Multi-Modal Knowledge Graph Construction Pipeline
│   │   ├── fusion.py               # Text-Visual graph fusion via spectral clustering
│   │   ├── img2graph.py            # Image vision & scene graph builder
│   │   ├── text2graph.py           # Text entity & relation extraction pipeline
│   │   └── utils.py                # Graph matrix transformations & spectral algorithms
│   ├── ingestion/                  # Multi-Modal Document Processors
│   │   ├── audio_preprocessing.py  # Audio transcription via OpenAI Whisper
│   │   ├── docx_preprocessing.py   # Microsoft Word document extractor
│   │   ├── excel_preprocessing.py  # Microsoft Excel sheet extractor
│   │   ├── image_preprocessing.py  # Standalone image metadata & vision loader
│   │   ├── image_utils.py          # Image compression & formatting utilities
│   │   └── pdf_preprocessing.py    # MinerU / PyMuPDF dual PDF parsing engine
│   ├── llm/                        # LLM Interface Layer
│   │   └── client.py               # OpenAI client wrapper & response caching system
│   ├── retrieval/                  # GraphRAG Retrieval Engine
│   │   └── query.py                # Semantic graph search & answer synthesis engine
│   ├── services/                   # Business Logic & Orchestration Services
│   │   ├── document_service.py     # Document management service
│   │   ├── multidocument_service.py # Multi-document graph fusion & batch indexing
│   │   ├── query_service.py        # Compliance query orchestration
│   │   └── workspace_document_service.py # Workspace document storage service
│   ├── storage/                    # Persistence Layer
│   │   ├── graph_storage.py        # NetworkX GraphML storage implementation
│   │   └── kv_storage.py           # Key-Value JSON cache storage implementation
│   ├── utils/                      # Shared Helper Utilities
│   │   └── base.py                 # Token counting, hashing, logging utilities
│   ├── visualization/              # Legacy / Standalone Web Explorer
│   │   ├── graph_explorer.html     # D3 force-directed visualizer template
│   │   └── server.py               # Flask visualization server runner
│   └── builder.py                  # MMKGBuilder main pipeline orchestrator
│
├── frontend/                       # React 19 Web Dashboard Application
│   ├── src/
│   │   ├── api/                    # Axios/Fetch backend API client wrappers
│   │   ├── auth/                   # Supabase authentication & token store
│   │   ├── components/             # UI components & @xyflow/react graph canvas
│   │   ├── hooks/                  # Custom hooks (e.g. useWorkspaceGuard)
│   │   ├── pages/                  # Application views (Dashboard, Graph, Query, Cases, Reports, Upload)
│   │   ├── App.tsx                 # Main router & layout shell
│   │   └── main.tsx                # Frontend entry point
│   ├── package.json                # Frontend dependencies & scripts
│   ├── tailwind.config.js          # Tailwind CSS styling configuration
│   └── vite.config.ts              # Vite dev server & API proxy config
│
├── data/                           # Runtime Working Data Directories (gitignored outputs)
│   ├── cache/                      # LLM response cache store
│   ├── input/                      # Default document input storage
│   ├── output/                     # GraphML & embedding outputs
│   └── working/                    # Intermediate build artifacts
│
├── eval/                           # Benchmark & Evaluation Suite
│   ├── evaluate.py                 # Evaluation execution script
│   └── gold_sample.json            # Reference benchmarks & ground-truth evaluation sets
│
├── examples/                       # Examples & Framework Documentation
│   ├── docqa_example.py            # End-to-end evaluation runner script
│   ├── example_input/              # Sample academic PDF & QA dataset
│   └── paper/                      # Architecture diagrams & framework paper
│
├── models/                         # Local embedding model directory (`all-MiniLM-L6-v2`)
├── scripts/                        # Utility & import verification scripts
├── tests/                          # Automated backend test suite
│
├── .env.example                    # Backend environment variable template
├── Dockerfile                      # Production Docker container build file
├── LICENSE                         # License terms
├── main.py                         # Root CLI entry point
├── pyproject.toml                  # Python package & Ruff linter configuration
├── render.yaml                     # Render.com web service deployment manifest
└── requirements.txt                # Python backend dependencies
```

---

## Environment Configuration

### Backend Environment Variables (`.env`)

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | OpenAI API key for text LLM, vision, and Whisper transcription |
| `COCKROACH_DATABASE_URL` | **Yes** | — | CockroachDB Cloud TLS URL for persistent graph, vector, and session memory |
| `OPENAI_MODEL` | No | `gpt-4o` | Primary OpenAI model |
| `LLM_API_BASE` | No | `https://api.openai.com/v1` | OpenAI API endpoint base |
| `MM_API_KEY` | No | `${OPENAI_API_KEY}` | Vision LLM API key override |
| `MM_MODEL_NAME` | No | `gpt-4o` | Vision model override |
| `EMBEDDING_MODEL_DIR` | No | `sentence-transformers/all-MiniLM-L6-v2` | SentenceTransformer model path or HuggingFace ID |
| `SUPABASE_URL` | **Yes** | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | **Yes** | — | Supabase anonymous API key |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | — | Supabase service role key (for backend admin operations) |
| `SUPABASE_JWT_SECRET` | **Yes** | — | Secret key to verify client Supabase JWT tokens |
| `ALLOWED_ORIGINS` | **Yes** | `http://localhost:5173` | Comma-separated list of allowed CORS origins |
| `DOCUMENT_STORAGE_BACKEND` | No | `local` | Set to `s3` to mirror raw uploads to a private AWS S3 bucket |
| `AWS_REGION` / `S3_DOCUMENT_BUCKET` | When using S3 | — | Region and private bucket for durable raw documents |
| `USE_MINERU` | No | `false` | Enable MinerU parser (`true`/`false`) |
| `INPUT_PDF_PATH` | No | `data/input/` | Input directory path |
| `WORKING_DIR` | No | `data/working` | Intermediate build directory |
| `CACHE_PATH` | No | `data/cache` | Cache directory |
| `OUTPUT_DIR` | No | `data/output` | GraphML & embeddings output directory |

### Frontend Environment Variables (`frontend/.env`)

Copy `frontend/.env.example` to `frontend/.env`:

```bash
cp frontend/.env.example frontend/.env
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_SUPABASE_URL` | **Yes** | — | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | **Yes** | — | Supabase anon key |
| `VITE_API_BASE` | No | `""` (proxied in dev) | Deployed backend URL (e.g. `https://api.example.com`). Leave empty in development to use Vite's dev proxy to `http://localhost:8000`. |

---

## Installation & Setup

### Prerequisites

- **Python**: Version `3.11` or higher (`3.12` recommended for containerized builds).
- **Node.js**: Version `18.0.0` or higher (`npm` included).
- **Supabase Account**: An active Supabase project with JWT authentication enabled.
- **OpenAI API Key**: An active key with access to `gpt-4o` and audio models.

---

### Backend Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/InnovaHack.git
   cd InnovaHack
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Python dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **(Optional) Install MinerU for advanced PDF layout extraction**:
   ```bash
   pip install -U "mineru[all]"
   ```
   *Note: If MinerU is not installed or `USE_MINERU=false`, the backend seamlessly falls back to PyMuPDF (`pymupdf`).*

### CockroachDB migration

Set `COCKROACH_DATABASE_URL` to your cluster connection string, then apply
[`backend/storage/migrations/001_cockroachdb_schema.sql`](backend/storage/migrations/001_cockroachdb_schema.sql)
before starting graph ingestion:

```bash
psql "$COCKROACH_DATABASE_URL" -f backend/storage/migrations/001_cockroachdb_schema.sql
```

You can run the same SQL file in the CockroachDB Cloud SQL shell. If using an
MCP client during development, connect that client to the cluster and execute
the migration through the server's discovered SQL tool; do not expose the
database URL to the frontend.

### CockroachDB Cloud MCP

Use CockroachDB Cloud's managed **streamable HTTP** MCP server from a real MCP
client (for example Cursor or Claude Code). Configure the client with the
cluster ID and either OAuth or a service-account API key:

```json
{
  "mcpServers": {
    "cockroachdb-cloud": {
      "type": "http",
      "url": "https://cockroachlabs.cloud/mcp",
      "headers": {
        "mcp-cluster-id": "<cluster-id>",
        "Authorization": "Bearer <service-account-api-key>"
      }
    }
  }
}
```

The client performs the MCP initialization and tool discovery handshake; do
not replace this with a raw HTTP SQL request. The tool names are discovered
from the connected server so they are not hard-coded in this repository.

5. **Configure environment variables**:
   Create `.env` based on `.env.example` and set your API keys and Supabase credentials.

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Configure frontend environment variables**:
   Create `frontend/.env` based on `frontend/.env.example`.

---

## Usage Instructions

### 1. Running the Full-Stack Web Application

#### Start the FastAPI Backend Server:
```bash
# From project root:
python -m backend.api.run
```
- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- ReDoc Docs: `http://localhost:8000/redoc`

#### Start the React Frontend Dashboard:
```bash
# From frontend/ directory:
npm run dev
```
- Open `http://localhost:5173` in your browser.

---

### 2. CLI Usage

The root `main.py` provides a CLI for command-line graph indexing, querying, and visualization:

```bash
# Build knowledge graph from a document (PDF, DOCX, XLSX, MP3, WAV, PNG)
python main.py -i data/input/compliance_report.pdf

# Query the knowledge graph via GraphRAG
python main.py -q "What are the primary compliance risks described in the document?"

# Force rebuild ignoring cache
python main.py -i data/input/compliance_report.pdf -f

# Specify custom working and output directories
python main.py -i data/input/compliance_report.pdf -w data/working -o data/output

# Run with verbose debugging logs
python main.py -i data/input/compliance_report.pdf -v
```

#### CLI Flag Reference

| Flag | Short | Description |
|------|-------|-------------|
| `--input` | `-i` | Input file path (`.pdf`, `.docx`, `.xlsx`, `.mp3`, `.wav`, `.png`, etc.) |
| `--query` | `-q` | RAG query string |
| `--serve` | `-s` | Launch standalone Flask visualization server |
| `--working-dir` | `-w` | Override working directory |
| `--output-dir` | `-o` | Override output directory |
| `--mmkg-name` | `-m` | Override knowledge graph output name |
| `--force` | `-f` | Force rebuild (bypass cache) |
| `--verbose` | `-v` | Enable verbose logging |
| `--port` | — | Server port for visualization server (default: `5000`) |

---

### 3. Standalone Visualization Server

To run the legacy/standalone Flask graph visualizer UI:

```bash
python main.py -s --port 5000
# Access interactive graph explorer at http://localhost:5000
```

---

### 4. Docker Deployment

Build and run the containerized backend using Docker:

```bash
# Build the Docker image
docker build -t innova-backend .

# Run the container
docker run -d -p 8000:8000 --env-file .env --name innova-backend-container innova-backend
```

---

### 5. Evaluation & Benchmarks

Run the built-in document Q&A evaluation benchmark:

```bash
# Run docqa evaluation script
python examples/docqa_example.py

# Run general evaluation pipeline
python eval/evaluate.py
```

---

## REST API Reference

The backend exposes a full suite of REST endpoints guarded by JWT authentication (`Bearer <token>`).

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | System status & app details |
| `GET` | `/health` | Service health & dependency check |
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login user & issue session token |

### Protected Workspace Endpoints (`Bearer <token>` required)

| Category | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| **Workspaces** | `GET` | `/api/workspaces` | List accessible user workspaces |
| | `POST` | `/api/workspaces` | Create a new workspace |
| | `GET` | `/api/workspaces/{id}` | Get workspace details |
| | `GET` | `/api/workspaces/{id}/audit` | Retrieve workspace audit logs |
| **Ingestion** | `POST` | `/api/workspace/upload` | Ingest document into workspace & trigger KG build |
| **GraphRAG** | `POST` | `/api/workspace/query` | Execute workspace GraphRAG query |
| | `GET` | `/api/workspace/graph` | Fetch graph nodes/edges for visual explorer |
| | `POST` | `/api/workspace/report` | Generate compliance report with citations & evidence |
| **Cases** | `GET` | `/api/cases` | List workspace compliance cases |
| | `POST` | `/api/cases` | Create a new compliance case |
| | `GET` | `/api/cases/{id}` | Retrieve case details & attached evidence |
| **Storage** | `GET` | `/api/storage/status` | Storage health & backend persistence status |

---

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
