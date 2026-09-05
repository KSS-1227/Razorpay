# Architecture — Enterprise Compliance Intelligence Platform

System architecture diagram reflecting the verified implementation of the Enterprise Compliance Intelligence Platform, its workspace-aware auth model, graph analytics engines, quantile machine learning forecasting pipeline, and multi-modal knowledge graph ingestion.

```mermaid
flowchart TD
    %% ─────────────────────────────────────────────────────────────────────────
    %% STYLING & CLASSES
    %% ─────────────────────────────────────────────────────────────────────────
    classDef clientStyle fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#f8fafc
    classDef authStyle fill:#451a03,stroke:#f59e0b,stroke-width:2px,color:#fef3c7
    classDef apiStyle fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f8fafc
    classDef engineDeterministic fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ecfdf5
    classDef engineLLM fill:#581c87,stroke:#a855f7,stroke-width:2px,color:#faf5ff
    classDef mlOffline fill:#312e81,stroke:#818cf8,stroke-width:1.5px,stroke-dasharray: 5 5,color:#eef2ff
    classDef storageStyle fill:#18181b,stroke:#71717a,stroke-width:2px,color:#f4f4f5
    classDef ingestionStyle fill:#1c1917,stroke:#78716c,stroke-width:1.5px,color:#fafaf9

    %% ─────────────────────────────────────────────────────────────────────────
    %% 1. CLIENT LAYER
    %% ─────────────────────────────────────────────────────────────────────────
    subgraph CLIENT["1. CLIENT LAYER (React / Vite Frontend)"]
        UI["Compliance Dashboard Page<br/>(src/pages/app/CompliancePage.tsx)"]
        UI_REC["Section 1: Reconciliation<br/>(Invoices vs Contracts & Structuring)"]
        UI_TAX["Section 2: Tax Matching<br/>(Line Items vs HSN Schedule)"]
        UI_QA["Section 3: Settlement Q&A<br/>(Payouts & UTR GraphRAG Chat)"]
        UI_FC["Section 4: Cash Forecast<br/>(Net Cashflow & 80% CI Range)"]
        UI_NAV["Unified Shell / Auth / Case Picker Context<br/>(AuthContext + localStorage innova_active_case_id)"]

        UI --- UI_REC
        UI --- UI_TAX
        UI --- UI_QA
        UI --- UI_FC
        UI --- UI_NAV
    end
    class CLIENT,UI,UI_REC,UI_TAX,UI_QA,UI_FC,UI_NAV clientStyle

    %% ─────────────────────────────────────────────────────────────────────────
    %% 2. AUTHENTICATION & AUTHORIZATION GATEWAY
    %% ─────────────────────────────────────────────────────────────────────────
    subgraph AUTH["2. AUTH BOUNDARY (JWT Bearer Token Gate)"]
        JWTSecurity["Supabase JWT Validator & Case Ownership Guard<br/>(backend/auth/middleware/jwt_middleware.py — get_current_user)"]
    end
    class AUTH,JWTSecurity authStyle

    CLIENT ==>|"HTTPS / JSON + Authorization: Bearer & X-Workspace-ID"| JWTSecurity

    %% ─────────────────────────────────────────────────────────────────────────
    %% 3. FASTAPI ROUTE LAYER (THIN HANDLERS)
    %% ─────────────────────────────────────────────────────────────────────────
    subgraph API["3. API LAYER (FastAPI Protected Routes — backend/api/routes/)"]
        ROUTE_REC["POST /api/workspace/{case_id}/reconcile<br/>(reconciliation.py)"]
        ROUTE_TAX["POST /api/workspace/{case_id}/tax-match<br/>(tax_matching.py)"]
        ROUTE_QA["POST /api/workspace/{case_id}/settlement-qa<br/>(workspace_settlement_qa.py)"]
        ROUTE_FC["POST /api/workspace/{case_id}/forecast<br/>(forecast.py)"]
        ROUTE_CF["POST /api/workspace/{case_id}/cashflow<br/>(cashflow.py)"]

        ROUTE_QUERY["POST /api/workspace/{case_id}/query<br/>(workspace_query.py)"]
        ROUTE_UP["POST /api/workspace/{case_id}/upload<br/>(workspace_upload.py)"]
    end
    class API,ROUTE_REC,ROUTE_TAX,ROUTE_QA,ROUTE_FC,ROUTE_CF,ROUTE_QUERY,ROUTE_UP apiStyle

    JWTSecurity ==> ROUTE_REC
    JWTSecurity ==> ROUTE_TAX
    JWTSecurity ==> ROUTE_QA
    JWTSecurity ==> ROUTE_FC
    JWTSecurity ==> ROUTE_CF
    JWTSecurity ==> ROUTE_QUERY
    JWTSecurity ==> ROUTE_UP

    %% ─────────────────────────────────────────────────────────────────────────
    %% 4. LOGIC & ANALYTICS LAYER (DECOUPLED ENGINES)
    %% ─────────────────────────────────────────────────────────────────────────
    subgraph LOGIC["4. LOGIC LAYER (Auth-Free Testable Domain Engines)"]
        ENG_REC["ReconciliationEngine<br/>(backend/compliance/reconciliation_engine.py)<br/>⚡ <i>no LLM calls — deterministic graph + regex</i>"]
        ENG_TAX["TaxMatcher<br/>(backend/compliance/tax_matcher.py)<br/>⚡ <i>no LLM calls — deterministic HSN rate match</i>"]
        ENG_FC["forecast_logic.py & features.py<br/>(backend/ml/forecast_logic.py)"]
        ENG_EXT["CashflowExtractor & aggregate_daily<br/>(backend/compliance/cashflow_extractor.py)<br/>⚡ <i>no LLM calls — deterministic time-series</i>"]

        ENG_RAG["WorkspaceDocumentService & GraphRAGQuery<br/>(backend/services/workspace_document_service.py)<br/>🤖 <i>Vector Retrieval + LLM System Prompt Addendum</i>"]
    end
    class ENG_REC,ENG_TAX,ENG_EXT engineDeterministic
    class ENG_FC apiStyle
    class ENG_RAG engineLLM

    ROUTE_REC -->|"reconcile()"| ENG_REC
    ROUTE_TAX -->|"match()"| ENG_TAX
    ENG_TAX -.->"Reuses _load_nodes(), _parse_amount(), _source_files()"| ENG_REC

    ROUTE_FC -->|"_build_latest_feature_row()"| ENG_FC
    ROUTE_FC -->|"extract()"| ENG_EXT
    ROUTE_CF -->|"extract()"| ENG_EXT
    ENG_FC -->|"Feeds daily aggregated series"| ENG_EXT

    ROUTE_QA -->|"query(system_prompt_addendum)"| ENG_RAG
    ROUTE_QUERY -->|"query()"| ENG_RAG

    %% Dual-path outcome annotation for Forecast
    ROUTE_FC -->|"≥14 days dated history & models present"| RESP_FC_REAL["Normal 200 Response:<br/>{forecast_net_cashflow, lower_bound, upper_bound, horizon_days, model_trained_on, low_data_warning}"]
    ROUTE_FC -->|"<14 days dated history"| RESP_FC_THIN["Informational 200 Response:<br/>{forecast_available: false, reason: 'insufficient historical data'}"]

    %% ─────────────────────────────────────────────────────────────────────────
    %% 5. ML ARTIFACTS (OFFLINE PRE-TRAINED SWIMLANE)
    %% ─────────────────────────────────────────────────────────────────────────
    subgraph ML_OFFLINE["5. ML ARTIFACTS (Offline Pre-Trained Swimlane — Not Request-Time)"]
        TRAIN_SCRIPT["train_forecaster.py<br/>(backend/ml/train_forecaster.py)<br/><i>Offline training pipeline</i>"]
        JOB_MODELS[("Quantile Regressors & Meta<br/>backend/ml/artifacts/<br/>• forecaster_p10.joblib<br/>• forecaster_p50.joblib<br/>• forecaster_p90.joblib<br/>• forecaster_meta.json")]

        TRAIN_SCRIPT -.->"Generates offline"| JOB_MODELS
    end
    class ML_OFFLINE,TRAIN_SCRIPT,JOB_MODELS mlOffline

    ENG_FC -.->"Read-only model load (_load_models / _load_meta)"| JOB_MODELS

    %% ─────────────────────────────────────────────────────────────────────────
    %% 6. DATA & STORAGE LAYER
    %% ─────────────────────────────────────────────────────────────────────────
    subgraph DATA_LAYER["6. DATA & STORAGE LAYER (Shared State)"]
        POOL["Shared Async Pool<br/>(backend/cockroach_graph_storage.py — _get_pool)"]
        COCKROACH[("CockroachDB Workspace Graph<br/>• graph_nodes (by case_id)<br/>• graph_edges (by case_id)")]
        LOCAL_FS[("Local Workspace Filesystem<br/>data/users/{user_id}/cases/{case_id}/working/<br/>• kv_store_text_chunks.json<br/>• raw documents & output artifacts")]
    end
    class DATA_LAYER,POOL,COCKROACH,LOCAL_FS storageStyle

    ENG_REC --> POOL
    ENG_TAX --> POOL
    ENG_EXT --> POOL
    ENG_RAG --> POOL
    POOL ==> COCKROACH

    ENG_REC -.->"Source file resolution"| LOCAL_FS
    ENG_TAX -.->"Source file resolution"| LOCAL_FS
    ENG_EXT -.->"Text chunk lookup"| LOCAL_FS
    ENG_RAG -.->"Document chunk retrieval"| LOCAL_FS

    %% ─────────────────────────────────────────────────────────────────────────
    %% 7. UPSTREAM INGESTION PIPELINE
    %% ─────────────────────────────────────────────────────────────────────────
    subgraph INGESTION["7. UPSTREAM INGESTION PIPELINE (MMGraphRAG)"]
        DOCS["Input Documents<br/>(PDF, DOCX, XLSX, PNG, MP3, WAV, etc.)"]
        BUILDER["MMKGBuilder / Pipeline<br/>(backend/builder.py & backend/core/)"]
        SCHEMA["Shared Entity & Relationship Schema<br/>(backend/core/prompt.py)<br/>• Finance: VENDOR, INVOICE, CONTRACT_AMOUNT, APPROVAL_LIMIT<br/>• Tax: TAX_LINE_ITEM, HSN_CODE, TAX_RATE, GST_NUMBER<br/>• Settlement: SETTLEMENT_AMOUNT, PAYOUT_STATUS, UTR_NUMBER"]

        DOCS --> BUILDER
        BUILDER --> SCHEMA
        BUILDER ==>|"Writes nodes, edges & KV chunks"| COCKROACH
        BUILDER ==>|"Writes text chunks KV store"| LOCAL_FS
    end
    class INGESTION,DOCS,BUILDER,SCHEMA ingestionStyle

    ROUTE_UP --> BUILDER
```

---

### Architectural Design Properties & Verified Contracts

1. **Deterministic Execution (No LLM Bottlenecks)**:
   - `ReconciliationEngine`, `TaxMatcher`, and `CashflowExtractor` operate via pure graph traversal and regular expressions over CockroachDB graph nodes and edges. They do **not** invoke LLM endpoints during evaluation, ensuring deterministic, ultra-fast compliance verification.

2. **Reusable Settlement Q&A Pathway**:
   - `POST /api/workspace/{case_id}/settlement-qa` delegates vector retrieval directly to `WorkspaceDocumentService.query()` without duplicating GraphRAG code. It injects a domain-specific settlement preamble into the system prompt *after* vector retrieval finishes so embedding resolution remains pure.

3. **Separation of Forecasting & Inference**:
   - `train_forecaster.py` runs strictly offline to generate LightGBM/Quantile regressors ($p_{10}, p_{50}, p_{90}$) and metadata into `backend/ml/artifacts/`.
   - `forecast.py` and `forecast_logic.py` load these artifacts read-only at request time.
   - **Dual-Path Handling**: If a case workspace has $<14$ days of dated financial event history, `forecast_logic.py` returns an honest `{"forecast_available": false, "reason": "insufficient historical data"}` response (HTTP 200) rather than failing or returning fabricated numbers.

4. **Shared Database & Connection Pool**:
   - All engines connect to CockroachDB through the shared async pool (`_get_pool` in `cockroach_graph_storage.py`). All tables (`graph_nodes`, `graph_edges`) are scoped strictly by `case_id`.

5. **Authentication Boundary**:
   - Every workspace route enforces the `Depends(get_current_user)` FastAPI dependency which validates the Supabase JWT bearer token and verifies case ownership (`get_case(case_id, user_id)`).
