-- CockroachDB storage schema for workspace-scoped documents, graph data,
-- vector retrieval, and conversational memory.

CREATE TABLE IF NOT EXISTS documents (
    workspace_id UUID NOT NULL,
    document_id UUID NOT NULL DEFAULT gen_random_uuid(),
    filename STRING NOT NULL,
    storage_key STRING NOT NULL,
    content_type STRING,
    size_bytes INT8,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, document_id)
);

CREATE TABLE IF NOT EXISTS graph_nodes (
    workspace_id UUID NOT NULL,
    node_id STRING NOT NULL,
    entity_type STRING,
    description STRING,
    source_id STRING,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, node_id)
);

CREATE TABLE IF NOT EXISTS graph_edges (
    workspace_id UUID NOT NULL,
    source_id STRING NOT NULL,
    target_id STRING NOT NULL,
    description STRING,
    weight FLOAT8,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, source_id, target_id)
);

CREATE TABLE IF NOT EXISTS entity_embeddings (
    workspace_id UUID NOT NULL,
    node_id STRING NOT NULL,
    embedding VECTOR(384) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, node_id)
);

CREATE VECTOR INDEX IF NOT EXISTS entity_embeddings_vector_idx
    ON entity_embeddings (workspace_id, embedding);

CREATE TABLE IF NOT EXISTS agent_memory (
    workspace_id UUID NOT NULL,
    session_id UUID NOT NULL,
    turn INT8 NOT NULL,
    question STRING NOT NULL,
    answer STRING NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, turn)
);

CREATE INDEX IF NOT EXISTS agent_memory_workspace_session_idx
    ON agent_memory (workspace_id, session_id, turn);
