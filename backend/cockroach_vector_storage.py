"""
CockroachDB-backed vector storage — replaces the local .npy file +
sklearn cosine_similarity previously used in retrieval/query.py.

Uses CockroachDB's native VECTOR type and the <=> cosine-distance
operator, matching the workspace_id-prefixed VECTOR INDEX defined in
schema.sql. Confirmed against CockroachDB's own docs (v26.2): <=> is
cosine distance, <-> is L2, <#> is negative inner product — this file
uses <=> to match vector_cosine similarity search.

Requires: pip install "psycopg[binary,pool]"   (same driver as
          cockroach_graph_storage.py — same cluster, same pool pattern)
Env var:  COCKROACH_DATABASE_URL
"""
import os

import psycopg
from psycopg_pool import AsyncConnectionPool

_DSN = os.environ.get("COCKROACH_DATABASE_URL")
_pool: AsyncConnectionPool | None = None


async def _get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        if not _DSN:
            raise RuntimeError(
                "COCKROACH_DATABASE_URL is not set. Get a free-tier connection "
                "string from the CockroachDB Cloud Console and set it as an "
                "env var before using cockroach_vector_storage."
            )
        _pool = AsyncConnectionPool(_DSN, min_size=1, max_size=10, open=False)
    if _pool.closed:
        await _pool.open()
    return _pool


def _to_vector_literal(embedding) -> str:
    """psycopg sends VECTOR columns as a bracketed literal string, e.g. '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"


async def nodes_missing_embeddings(workspace_id: str) -> list[tuple[str, str]]:
    """
    Return (node_id, description) for every node in this workspace's graph
    that doesn't have an embedding row yet. Called after extraction so only
    genuinely new entities get (re-)encoded — mirrors the same
    "only touch what's new" pattern as the chunk-extraction tracking in
    builder.py's _step_text_extraction.
    """
    pool = await _get_pool()
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            """
            SELECT n.node_id, n.description
            FROM graph_nodes n
            LEFT JOIN entity_embeddings e
              ON e.workspace_id = n.workspace_id AND e.node_id = n.node_id
            WHERE n.workspace_id = %s AND e.node_id IS NULL
            """,
            (workspace_id,),
        )).fetchall()
        return [(r[0], r[1] or r[0]) for r in rows]


async def upsert_embedding(workspace_id: str, node_id: str, embedding) -> None:
    pool = await _get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO entity_embeddings (workspace_id, node_id, embedding, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (workspace_id, node_id) DO UPDATE SET
                embedding  = excluded.embedding,
                updated_at = now()
            """,
            (workspace_id, node_id, _to_vector_literal(embedding)),
        )


async def top_k_similar(workspace_id: str, query_embedding, k: int = 5) -> list[tuple[str, float]]:
    """
    Return [(node_id, similarity)] ordered most-similar-first, using the
    workspace_id-prefixed distributed vector index. <=> returns cosine
    DISTANCE (0 = identical, 2 = opposite) — converted to similarity
    (1 - distance) here so callers get the same 0..1-higher-is-better
    scale the old sklearn cosine_similarity() call returned.
    """
    pool = await _get_pool()
    qvec = _to_vector_literal(query_embedding)
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            """
            SELECT node_id, 1 - (embedding <=> %s) AS similarity
            FROM entity_embeddings
            WHERE workspace_id = %s
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (qvec, workspace_id, qvec, k),
        )).fetchall()
        return [(r[0], float(r[1])) for r in rows]