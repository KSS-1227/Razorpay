"""Focused offline tests for Cockroach storage adapters and conversation turns."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import networkx as nx

from backend import memory
from backend.cockroach_graph_storage import CockroachGraphStorage
from backend.retrieval.query import GraphRAGQuery
from backend.services.workspace_document_service import WorkspaceDocumentService


class _AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _GraphConnection:
    async def execute(self, query, _params):
        return _GraphCursor(query)


class _GraphCursor:
    def __init__(self, query):
        self.query = query

    async def fetchall(self):
        if "FROM graph_nodes" in self.query:
            return [("control-1", "CONTROL", "Access control", "chunk-1")]
        return [("control-1", "policy-1", "governs", 0.8)]


class _GraphPool:
    closed = False

    def connection(self):
        return _AsyncContext(_GraphConnection())


class _ReplaceConnection:
    def __init__(self):
        self.statements = []

    async def execute(self, query, _params):
        self.statements.append(query)


class _ReplacePool:
    def __init__(self):
        self.connection_instance = _ReplaceConnection()

    def connection(self):
        return _AsyncContext(self.connection_instance)


class _MemoryConnection:
    def __init__(self):
        self.rows: list[tuple[int, str, str]] = []

    async def execute(self, query, params):
        if query.lstrip().startswith("SELECT COALESCE"):
            return _MemoryCursor([(max((row[0] for row in self.rows), default=0) + 1,)])
        if "SELECT turn, question, answer" in query:
            return _MemoryCursor(self.rows)
        if query.lstrip().startswith("INSERT INTO agent_memory"):
            turn, question, answer = params[2:]
            if not any(row[0] == turn for row in self.rows):
                self.rows.append((turn, question, answer))
            return _MemoryCursor([])
        raise AssertionError(query)


class _MemoryCursor:
    def __init__(self, rows):
        self.rows = rows

    async def fetchone(self):
        return self.rows[0]

    async def fetchall(self):
        return sorted(self.rows)


class _MemoryPool:
    def __init__(self):
        self.connection_instance = _MemoryConnection()

    def connection(self):
        return _AsyncContext(self.connection_instance)


class CockroachAdapterTests(unittest.TestCase):
    def test_graph_export_writes_graphml_snapshot(self):
        async def run():
            storage = CockroachGraphStorage(
                namespace="chunk_entity_relation",
                workspace_id="00000000-0000-0000-0000-000000000001",
            )

            async def pool():
                return _GraphPool()

            storage._pool = pool
            with tempfile.TemporaryDirectory() as tmp:
                destination = Path(tmp) / "graph.graphml"
                await storage.export_graphml(str(destination))
                graph = nx.read_graphml(destination)
                self.assertEqual(graph.number_of_nodes(), 2)
                self.assertEqual(graph.number_of_edges(), 1)

        asyncio.run(run())

    def test_memory_turns_are_sequential_and_retrievable(self):
        async def run():
            pool = _MemoryPool()

            async def get_pool():
                return pool

            original = memory._get_pool
            memory._get_pool = get_pool
            try:
                self.assertEqual(
                    await memory.save_turn("workspace", "session", "first", "answer one"), 1
                )
                self.assertEqual(
                    await memory.save_turn("workspace", "session", "second", "answer two"), 2
                )
                history = await memory.get_session_history("workspace", "session")
                self.assertEqual([turn["turn"] for turn in history], [1, 2])
            finally:
                memory._get_pool = original

        asyncio.run(run())

    def test_fused_snapshot_replaces_graph_and_stale_vectors(self):
        async def run():
            storage = CockroachGraphStorage(
                namespace="chunk_entity_relation",
                workspace_id="00000000-0000-0000-0000-000000000001",
            )
            pool = _ReplacePool()

            async def get_pool():
                return pool

            storage._pool = get_pool
            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / "fused.graphml"
                graph = nx.Graph()
                graph.add_edge("control-1", "policy-1", description="governs", weight=0.8)
                nx.write_graphml(graph, source)
                await storage.replace_from_graphml(str(source))

            statements = "\n".join(pool.connection_instance.statements)
            self.assertIn("DELETE FROM entity_embeddings", statements)
            self.assertIn("INSERT INTO graph_nodes", statements)
            self.assertIn("INSERT INTO graph_edges", statements)

        asyncio.run(run())

    def test_query_reports_missing_snapshot_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.graphml"
            with self.assertRaises(FileNotFoundError):
                GraphRAGQuery(
                    graph_path=str(missing),
                    workspace_id="00000000-0000-0000-0000-000000000001",
                )

    def test_workspace_follow_up_includes_history_and_saves_next_turn(self):
        class Workspace:
            def __init__(self, root):
                self.working = root / "working"
                self.output = root / "output"
                self.cache = root / "cache"
                for path in (self.working, self.output, self.cache):
                    path.mkdir()

            def graph_exists(self):
                return True

        class Engine:
            question = ""

            def __init__(self, **_kwargs):
                self.graph = nx.Graph()
                self.text_chunks = {}
                self.image_data = {}

            async def query(self, question, **_kwargs):
                Engine.question = question
                return {
                    "answer": "follow-up answer",
                    "retrieval": {
                        "similar_nodes": [], "node_datas": [],
                        "entities_context": "", "sources_context": "",
                        "relationships_context": "",
                    },
                }

        async def history(_workspace_id, _session_id):
            return [{"turn": 1, "question": "first", "answer": "earlier answer"}]

        async def save(_workspace_id, _session_id, _question, _answer):
            return 2

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                ws = Workspace(root)
                (ws.output / "example_mmkg.graphml").write_text("snapshot")
                service = object.__new__(WorkspaceDocumentService)
                service.user_id = "user"
                service.case_id = "00000000-0000-0000-0000-000000000001"
                service.ws = ws
                with (
                    patch("backend.services.workspace_document_service.GraphRAGQuery", Engine),
                    patch("backend.services.workspace_document_service.EvidenceEngine") as evidence,
                    patch("backend.memory.get_session_history", history),
                    patch("backend.memory.save_turn", save),
                ):
                    evidence.return_value.collect.return_value = {"entities": []}
                    result = await service.query("follow-up", session_id="session")

            self.assertIn("earlier answer", Engine.question)
            self.assertIn("Current question: follow-up", Engine.question)
            self.assertEqual(result["turn"], 2)

        asyncio.run(run())
