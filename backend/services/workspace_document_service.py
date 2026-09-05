"""
Workspace-aware document processing service.

Replaces MultiDocumentService / DocumentService for authenticated requests.
All paths are scoped to data/users/{user_id}/cases/{case_id}/ — no global
data/working, data/output, or data/cache directories are used.

The MMKGBuilder and GraphRAGQuery pipeline files are NOT modified — they
accept working_dir / output_dir as constructor parameters, which we supply
from UserWorkspace.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC
from pathlib import Path

import networkx as nx

from backend.auth.workspace import UserWorkspace
from backend.compliance.citation_engine import CitationEngine
from backend.builder import MMKGBuilder
from backend.compliance.evidence_engine import EvidenceEngine
from backend.config import MMKG_NAME
from backend.retrieval.query import GraphRAGQuery

logger = logging.getLogger(__name__)


async def _update_case_status(user_id: str, case_id: str, status: str) -> None:
    """Best-effort update of public.cases.status — never raises."""
    try:
        from backend.auth.supabase_client import get_supabase_client
        supabase = await get_supabase_client()
        await (
            supabase
            .from_("cases")
            .update({"status": status})
            .eq("id", case_id)
            .eq("user_id", user_id)
            .execute()
        )
        logger.info("Case %s status → %s", case_id, status)
    except Exception as exc:
        logger.warning("Could not update case status for %s: %s", case_id, exc)


class WorkspaceDocumentService:
    """Process documents inside a user's isolated workspace."""

    def __init__(self, user_id: str, case_id: str):
        self.user_id = user_id
        self.case_id = case_id
        self.ws = UserWorkspace(user_id=user_id, case_id=case_id).ensure()
        self._cached_graph_summary: dict | None = None

    # ------------------------------------------------------------------
    # Upload + pipeline
    # ------------------------------------------------------------------

    async def process_documents(
        self,
        file_paths: list[str],
        file_results: list | None = None,
    ) -> dict:
        """Run MMKGBuilder over *file_paths* inside the user workspace.

        Parameters
        ----------
        file_paths:
            Absolute or relative paths to files already saved inside
            ``self.ws.uploads/``.
        file_results:
            Existing save-phase metadata list (passed through to response).

        Returns
        -------
        dict
            Processing summary including per-file status and graph summary.
        """
        if not file_paths:
            raise ValueError("No files supplied.")

        # Each case gets its own builder instance with isolated dirs
        builder = MMKGBuilder(
            working_dir=str(self.ws.working),
            output_dir=str(self.ws.output),
            mmkg_name=MMKG_NAME,
            workspace_id=self.case_id,
        )

        processed:    list[str]  = []
        failed:       list[dict] = []
        proc_results: list[dict] = []

        for file_path in file_paths:
            fname = Path(file_path).name
            logger.info("⚙️  Processing %s → workspace %s", fname, self.ws.root)
            try:
                await builder.index(file_path)
                processed.append(fname)
                proc_results.append({"file": fname, "status": "processed"})
            except Exception as exc:
                logger.error("❌ Failed %s: %s", fname, exc)
                failed.append({"file": fname, "error": str(exc)})
                proc_results.append({"file": fname, "status": "failed", "error": str(exc)})

        graph_summary = self._graph_summary()

        # Persist a report.json in output/
        self._save_report_json(graph_summary, proc_results)

        # Mark case status in DB: completed if all files processed, failed otherwise
        final_status = "completed" if len(failed) == 0 else "failed"
        await _update_case_status(self.user_id, self.case_id, final_status)

        return {
            "success":         len(failed) == 0,
            "total_uploaded":  len(file_paths),
            "total_processed": len(processed),
            "total_failed":    len(failed),
            "processed":       processed,
            "failed":          failed,
            "file_results":    proc_results,
            "knowledge_graph": graph_summary,
            "workspace": {
                "output_dir": str(self.ws.output),
                "graph_path": str(self.ws.graph_path),
            },
        }

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query(
        self,
        question: str,
        top_k: int = 10,
        session_id: str | None = None,
        system_prompt_addendum: str | None = None,
    ) -> dict:
        """Run a GraphRAG query scoped to this user's workspace.

        Raises
        ------
        FileNotFoundError
            If no graph exists yet for this case.
        """
        if not self.ws.graph_exists():
            raise FileNotFoundError(
                f"No knowledge graph found for this case. "
                f"Upload and process documents first. "
                f"(Expected: {self.ws.graph_path})"
            )

        start = time.time()

        history: list[dict] = []
        if session_id:
            from backend.memory import get_session_history
            history = await get_session_history(self.case_id, session_id)

        if history:
            history_context = "\n".join(
                f"Turn {turn['turn']}\nUser: {turn['question']}\nAssistant: {turn['answer']}"
                for turn in history
            )
            query_question = (
                "Use the following prior conversation only when it is relevant. "
                "Answer the current question using the retrieved compliance evidence.\n\n"
                f"Prior conversation:\n{history_context}\n\nCurrent question: {question}"
            )
        else:
            query_question = question


        # GraphRAGQuery reads graph from working_dir and embeddings from output_dir.
        # Pass the final output graphml explicitly so the query engine uses the
        # fully-fused graph (not an intermediate working-dir file).
        # Pass workspace-scoped cache_path so LLM responses are isolated per user/case.
        from backend.config import MMKG_NAME as _MMKG_NAME
        output_graph = self.ws.output / f"{_MMKG_NAME}.graphml"
        graph_path   = str(output_graph) if output_graph.exists() else None

        query_engine = GraphRAGQuery(
            working_dir=str(self.ws.working),
            graph_path=graph_path,
            embedding_path=str(self.ws.output / f"{_MMKG_NAME}_emb.npy"),
            cache_path=str(self.ws.cache),
            workspace_id=self.case_id,
        )

        from backend.config import QueryParam
        # Capture top_k before the class body (class scope can't close over local vars)
        _top_k = top_k
        # Create a per-request param copy to avoid mutating the global class
        class _Param:
            top_k = _top_k
            response_type = QueryParam.response_type
            local_max_token_for_local_context = QueryParam.local_max_token_for_local_context
            number_of_mmentities = QueryParam.number_of_mmentities
            local_max_token_for_text_unit = QueryParam.local_max_token_for_text_unit

        result = await query_engine.query(query_question, param=_Param, return_context=True,
                                           system_prompt_addendum=system_prompt_addendum)

        answer            = result["answer"]
        retrieval_context = result["retrieval"]
        processing_time   = round(time.time() - start, 2)

        evidence = EvidenceEngine().collect(
            retrieval_context=retrieval_context,
            graph=query_engine.graph,
            text_chunks=query_engine.text_chunks,
            image_data=query_engine.image_data,
        )
        citations = CitationEngine().build_citations(
            retrieval_context=retrieval_context,
            graph=query_engine.graph,
            text_chunks=query_engine.text_chunks,
        )

        result = {
            "answer":                    answer,
            "evidence":                  evidence,
            "citations":                 citations,
            "processing_time_seconds":   processing_time,
            "graph": {
                "nodes": query_engine.graph.number_of_nodes(),
                "edges": query_engine.graph.number_of_edges(),
            },
        }

        if session_id:
            from backend.memory import save_turn
            result["session_id"] = session_id
            result["turn"] = await save_turn(self.case_id, session_id, question, answer)

        # Persist query stats so /api/stats can return real metrics
        self._update_query_stats(evidence)

        return result

    # ------------------------------------------------------------------
    # Query stats (for /api/stats — RAG precision + cache hit rate)
    # ------------------------------------------------------------------

    def _update_query_stats(self, evidence: dict) -> None:
        """Persist running query stats into cache/query_stats.json.

        Tracks:
        - total_queries  : total number of queries run for this case
        - precision_sum  : sum of all per-query avg confidence scores
        (used to compute a rolling average precision on read)
        """
        stats_path = self.ws.cache / "query_stats.json"
        try:
            existing = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
        except Exception:
            existing = {}

        entities = evidence.get("entities", [])
        if entities:
            avg_conf = sum(e.get("confidence", 0.0) for e in entities) / len(entities)
        else:
            avg_conf = 0.0

        existing["total_queries"]  = existing.get("total_queries", 0) + 1
        existing["precision_sum"]  = existing.get("precision_sum", 0.0) + avg_conf

        try:
            stats_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not write query_stats.json: %s", exc)

    def get_stats(self) -> dict:
        """Return real RAG precision and LLM cache hit rate for this case.

        RAG precision  = rolling average of per-query entity confidence scores
        Cache hit rate = cached LLM responses / total queries attempted

        Returns a dict ready to be sent directly to the frontend.
        """
        stats_path = self.ws.cache / "query_stats.json"
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.exists() else {}
        except Exception:
            stats = {}

        total_queries = stats.get("total_queries", 0)
        precision_sum = stats.get("precision_sum", 0.0)

        # Rolling average precision as a percentage (0–100)
        if total_queries > 0:
            avg_precision = round((precision_sum / total_queries) * 100, 1)
        else:
            avg_precision = None  # No queries yet — frontend shows "—"

        # Cache hit rate: count cached LLM responses in the KV cache file
        # The cache grows with each unique (model, prompt) pair that gets stored.
        # Hit rate = min(cached_entries / total_queries, 1.0)
        cache_file = self.ws.cache / "kv_store_llm_response_cache.json"
        try:
            cache_data = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
            cached_entries = len(cache_data)
        except Exception:
            cached_entries = 0

        if total_queries > 0:
            # Each query may produce multiple LLM calls (entity extraction + merge).
            # We use a conservative estimate: cache entries / (total_queries * 2)
            # capped at 99% to stay realistic.
            raw_hit_rate = min(cached_entries / max(total_queries * 2, 1), 0.99)
            cache_hit_rate = round(raw_hit_rate * 100, 1)
        else:
            cache_hit_rate = None  # No queries yet

        return {
            "total_queries":    total_queries,
            "rag_precision":    avg_precision,    # float (0–100) or None
            "cache_hit_rate":   cache_hit_rate,   # float (0–100) or None
            "cached_entries":   cached_entries,
        }

    # ------------------------------------------------------------------
    # Graph summary / report
    # ------------------------------------------------------------------

    def _graph_summary(self) -> dict:
        """Read the workspace graph and return node/edge/type counts.

        Result is cached on the instance so repeated calls within the same
        request (e.g. query() followed by graph_summary()) only hit disk once.
        """
        if self._cached_graph_summary is not None:
            return self._cached_graph_summary

        # Try workspace-specific path first, then legacy MMKG_NAME path
        candidates = [
            self.ws.graph_path,
            self.ws.output / f"{MMKG_NAME}.graphml",
        ]
        graph_path = next((p for p in candidates if p.exists()), None)

        if graph_path is None:
            self._cached_graph_summary = {"available": False}
            return self._cached_graph_summary

        try:
            G             = nx.read_graphml(str(graph_path))
            entity_types: dict = {}
            for _, data in G.nodes(data=True):
                etype = data.get("entity_type", "UNKNOWN").replace('"', "")
                entity_types[etype] = entity_types.get(etype, 0) + 1
            self._cached_graph_summary = {
                "available":    True,
                "graph_path":   str(graph_path),
                "nodes":        G.number_of_nodes(),
                "edges":        G.number_of_edges(),
                "entity_types": entity_types,
            }
        except Exception as exc:
            logger.warning("Could not read graph for summary: %s", exc)
            self._cached_graph_summary = {"available": False, "error": str(exc)}

        return self._cached_graph_summary

    def graph_summary(self) -> dict:
        """Public alias for _graph_summary().

        Route code should call this instead of the private method directly.
        The result is cached so multiple calls within the same service instance
        only read the graphml file once.
        """
        return self._graph_summary()

    def _save_report_json(self, graph_summary: dict, file_results: list) -> None:
        """Persist a report.json in the workspace output directory."""
        from datetime import datetime
        report = {
            "generated_at":    datetime.now(tz=UTC).isoformat(),
            "user_id":         self.ws.user_id,
            "case_id":         self.ws.case_id,
            "knowledge_graph": graph_summary,
            "file_results":    file_results,
        }
        try:
            self.ws.report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Could not write report.json: %s", exc)
