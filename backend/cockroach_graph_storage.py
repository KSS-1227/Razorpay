"""
CockroachDB-backed graph storage — drop-in replacement for NetworkXStorage.

Same interface as storage/graph_storage.py's NetworkXStorage, so it can be
swapped in without touching builder.py, text2graph.py, or fusion.py at all.
Those files only ever call the BaseGraphStorage methods below — they don't
know or care whether the graph lives in a local .graphml file or in
CockroachDB rows.

Requires: pip install "psycopg[binary,pool]"
Env var:  COCKROACH_DATABASE_URL="postgresql://user:pass@host:26257/defaultdb?sslmode=verify-full"
          (get this from the CockroachDB Cloud Console, free-tier cluster)

Usage — same call sites as NetworkXStorage, just swap the class:
    self.graph = CockroachGraphStorage(
        namespace="chunk_entity_relation",
        workspace_id=workspace_id,   # NEW — required, scopes every query
    )
"""
import os
from dataclasses import dataclass

import networkx as nx
import psycopg
from psycopg_pool import AsyncConnectionPool

from .storage.graph_storage import BaseGraphStorage

_DSN = os.environ.get("COCKROACH_DATABASE_URL")
_pool: AsyncConnectionPool | None = None


def _get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        if not _DSN:
            raise RuntimeError(
                "COCKROACH_DATABASE_URL is not set. Get a free-tier connection "
                "string from the CockroachDB Cloud Console and set it as an "
                "env var before using CockroachGraphStorage."
            )
        _pool = AsyncConnectionPool(_DSN, min_size=1, max_size=10, open=False)
    return _pool


@dataclass
class CockroachGraphStorage(BaseGraphStorage):
    workspace_id: str = None  # required — scopes every row so workspaces never mix

    def __post_init__(self):
        if not self.workspace_id:
            raise ValueError("CockroachGraphStorage requires workspace_id")

    async def _pool(self):
        pool = _get_pool()
        if pool.closed:  # psycopg_pool lazy-open
            await pool.open()
        return pool

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def has_node(self, node_id: str) -> bool:
        pool = await self._pool()
        async with pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT 1 FROM graph_nodes WHERE workspace_id=%s AND node_id=%s",
                (self.workspace_id, node_id),
            )).fetchone()
            return row is not None

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        pool = await self._pool()
        async with pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT 1 FROM graph_edges WHERE workspace_id=%s AND source_id=%s AND target_id=%s",
                (self.workspace_id, source_node_id, target_node_id),
            )).fetchone()
            return row is not None

    async def get_node(self, node_id: str) -> dict | None:
        pool = await self._pool()
        async with pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT entity_type, description, source_id FROM graph_nodes "
                "WHERE workspace_id=%s AND node_id=%s",
                (self.workspace_id, node_id),
            )).fetchone()
            if not row:
                return None
            return {"entity_type": row[0], "description": row[1], "source_id": row[2]}

    async def get_edge(self, source_node_id: str, target_node_id: str) -> dict | None:
        pool = await self._pool()
        async with pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT description, weight, source_id FROM graph_edges "
                "WHERE workspace_id=%s AND source_id=%s AND target_id=%s",
                (self.workspace_id, source_node_id, target_node_id),
            )).fetchone()
            if not row:
                return None
            return {
                "description": row[0],
                "weight":      row[1],
                "source_id":   row[2] or "",
                "order":       1,          # order not stored in DB; default to 1
            }

    async def get_node_edges(self, source_node_id: str):
        pool = await self._pool()
        async with pool.connection() as conn:
            rows = await (await conn.execute(
                "SELECT source_id, target_id FROM graph_edges "
                "WHERE workspace_id=%s AND (source_id=%s OR target_id=%s)",
                (self.workspace_id, source_node_id, source_node_id),
            )).fetchall()
            return [(r[0], r[1]) for r in rows] or None

    async def node_degree(self, node_id: str) -> int:
        edges = await self.get_node_edges(node_id)
        return len(edges) if edges else 0

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        return await self.node_degree(src_id) + await self.node_degree(tgt_id)

    # ------------------------------------------------------------------
    # Writes — this is the actual "dynamic graph" behavior: UPSERT means
    # a second document's entities are added to the existing row set,
    # never overwriting the whole table.
    # ------------------------------------------------------------------

    async def upsert_node(self, node_id: str, node_data: dict[str, str]):
        pool = await self._pool()
        async with pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO graph_nodes (workspace_id, node_id, entity_type, description, source_id, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (workspace_id, node_id) DO UPDATE SET
                    entity_type = excluded.entity_type,
                    description = excluded.description,
                    source_id   = excluded.source_id,
                    updated_at  = now()
                """,
                (
                    self.workspace_id,
                    node_id,
                    node_data.get("entity_type"),
                    node_data.get("description"),
                    node_data.get("source_id"),
                ),
            )

    async def upsert_edge(self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]):
        pool = await self._pool()
        async with pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO graph_edges (workspace_id, source_id, target_id, description, weight, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (workspace_id, source_id, target_id) DO UPDATE SET
                    description = excluded.description,
                    weight      = excluded.weight,
                    updated_at  = now()
                """,
                (
                    self.workspace_id,
                    source_node_id,
                    target_node_id,
                    edge_data.get("description"),
                    edge_data.get("weight"),
                ),
            )

    async def export_graphml(self, destination: str) -> None:
        """Write this workspace's CockroachDB graph as a NetworkX GraphML snapshot."""
        pool = await self._pool()
        async with pool.connection() as conn:
            node_rows = await (await conn.execute(
                "SELECT node_id, entity_type, description, source_id FROM graph_nodes WHERE workspace_id=%s",
                (self.workspace_id,),
            )).fetchall()
            edge_rows = await (await conn.execute(
                "SELECT source_id, target_id, description, weight FROM graph_edges WHERE workspace_id=%s",
                (self.workspace_id,),
            )).fetchall()

        graph = nx.Graph()
        for node_id, entity_type, description, source_id in node_rows:
            graph.add_node(node_id, entity_type=entity_type or "UNKNOWN", description=description or "", source_id=source_id or "")
        for source_id, target_id, description, weight in edge_rows:
            graph.add_edge(source_id, target_id, description=description or "", weight=float(weight) if weight is not None else 1.0)
        nx.write_graphml(graph, destination)

    async def replace_from_graphml(self, source: str) -> None:
        """Replace this workspace's database graph with a fused GraphML snapshot."""
        graph = nx.read_graphml(source)
        pool = await self._pool()
        async with pool.connection() as conn:
            await conn.execute(
                "DELETE FROM entity_embeddings WHERE workspace_id=%s",
                (self.workspace_id,),
            )
            await conn.execute(
                "DELETE FROM graph_edges WHERE workspace_id=%s",
                (self.workspace_id,),
            )
            await conn.execute(
                "DELETE FROM graph_nodes WHERE workspace_id=%s",
                (self.workspace_id,),
            )
            for node_id, data in graph.nodes(data=True):
                await conn.execute(
                    """
                    INSERT INTO graph_nodes (workspace_id, node_id, entity_type, description, source_id, updated_at)
                    VALUES (%s, %s, %s, %s, %s, now())
                    """,
                    (
                        self.workspace_id,
                        node_id,
                        data.get("entity_type", "UNKNOWN"),
                        data.get("description", ""),
                        data.get("source_id", ""),
                    ),
                )
            for source_id, target_id, data in graph.edges(data=True):
                await conn.execute(
                    """
                    INSERT INTO graph_edges (workspace_id, source_id, target_id, description, weight, updated_at)
                    VALUES (%s, %s, %s, %s, %s, now())
                    """,
                    (
                        self.workspace_id,
                        source_id,
                        target_id,
                        data.get("description", ""),
                        data.get("weight", 1.0),
                    ),
                )

    async def index_done_callback(self):
        # CockroachDB already persisted every upsert individually — nothing batched to flush.
        # Optionally write a local GraphML snapshot for debugging if storage_dir is set.
        if not self.storage_dir:
            return
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            await self.export_graphml(
                os.path.join(self.storage_dir, f"graph_{self.namespace}.graphml")
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "CockroachGraphStorage: could not write GraphML snapshot: %s", exc
            )
