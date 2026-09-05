"""
MultiDocumentService

Enterprise Compliance Intelligence Platform

Purpose
-------
Process multiple heterogeneous enterprise documents and build a single
unified Knowledge Graph.

The actual preprocessing is delegated to MMKGBuilder, which handles
format detection internally.  This service is responsible for:
  - Iterating over all files sequentially
  - Tolerating individual file failures (continue on error)
  - Returning per-file processing status
  - Returning a graph summary once all files are processed
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import networkx as nx

from backend.builder import MMKGBuilder
from backend.config import settings

logger = logging.getLogger(__name__)


class MultiDocumentService:
    """Legacy upload service, scoped by its upload-session case ID."""

    @staticmethod
    def _case_dirs(case_id: str) -> tuple[Path, Path]:
        """Return isolated working and output directories for one upload case."""
        case_root = Path("data/uploads") / case_id
        return case_root / "working", case_root / "output"

    # ------------------------------------------------------------------
    # Primary entry point — sequential processing
    # ------------------------------------------------------------------

    async def process_documents(
        self,
        file_paths: list[str],
        case_id: str = "",
        file_results: list | None = None,
    ) -> dict:
        """
        Process every file in *file_paths* through MMKGBuilder.

        Parameters
        ----------
        file_paths   : saved file paths to process
        case_id      : upload session identifier (informational)
        file_results : existing save-phase results list — used to match
                       filenames when reporting per-file processing status

        Returns
        -------
        dict with keys:
            success, processed, failed, total_uploaded, total_processed,
            file_results, knowledge_graph
        """
        if not file_paths:
            raise ValueError("No files supplied.")
        if not case_id:
            raise ValueError("MultiDocumentService requires case_id as workspace_id")

        working_dir, output_dir = self._case_dirs(case_id)
        builder = MMKGBuilder(
            working_dir=str(working_dir),
            output_dir=str(output_dir),
            workspace_id=case_id,
        )

        processed:    list[str]  = []
        failed:       list[dict] = []
        proc_results: list[dict] = []

        for file_path in file_paths:
            fname = Path(file_path).name
            logger.info(f"⚙️  [{case_id}] Processing: {fname}")
            try:
                await builder.index(file_path)
                processed.append(fname)
                proc_results.append({"file": fname, "status": "processed"})
                logger.info(f"✅ [{case_id}] Done: {fname}")
            except Exception as exc:
                logger.error(f"❌ [{case_id}] Failed: {fname} — {exc}")
                failed.append({"file": fname, "error": str(exc)})
                proc_results.append({"file": fname, "status": "failed", "error": str(exc)})

        graph_summary = self._graph_summary(output_dir)

        return {
            "success":          len(failed) == 0,
            "total_uploaded":   len(file_paths),
            "total_processed":  len(processed),
            "total_failed":     len(failed),
            "processed":        processed,
            "failed":           failed,
            "file_results":     proc_results,
            "knowledge_graph":  graph_summary,
        }

    # ------------------------------------------------------------------
    # Optional concurrent processing
    # ------------------------------------------------------------------

    async def process_concurrent(
        self,
        file_paths: list[str],
        case_id: str = "",
        max_workers: int = 3,
    ) -> dict:
        """
        Concurrent variant — use only if confirmed pipeline is safe.
        Sequential processing via process_documents() is the default.
        """
        if not case_id:
            raise ValueError("MultiDocumentService requires case_id as workspace_id")

        working_dir, output_dir = self._case_dirs(case_id)
        builder = MMKGBuilder(
            working_dir=str(working_dir),
            output_dir=str(output_dir),
            workspace_id=case_id,
        )
        semaphore    = asyncio.Semaphore(max_workers)
        processed:   list[str]  = []
        failed:      list[dict] = []
        proc_results: list[dict] = []

        async def _run(path: str):
            fname = Path(path).name
            async with semaphore:
                try:
                    await builder.index(path)
                    processed.append(fname)
                    proc_results.append({"file": fname, "status": "processed"})
                except Exception as exc:
                    failed.append({"file": fname, "error": str(exc)})
                    proc_results.append({"file": fname, "status": "failed", "error": str(exc)})

        await asyncio.gather(*(_run(p) for p in file_paths))

        graph_summary = self._graph_summary(output_dir)

        return {
            "success":         len(failed) == 0,
            "total_uploaded":  len(file_paths),
            "total_processed": len(processed),
            "total_failed":    len(failed),
            "processed":       processed,
            "failed":          failed,
            "file_results":    proc_results,
            "knowledge_graph": graph_summary,
        }

    # ------------------------------------------------------------------
    # Graph summary
    # ------------------------------------------------------------------

    def _graph_summary(self, output_dir: Path) -> dict:
        """Read the generated GraphML and return node/edge/type counts."""
        graph_path = output_dir / f"{settings.MMKG_NAME}.graphml"
        if not graph_path.exists():
            return {"available": False}

        try:
            G            = nx.read_graphml(str(graph_path))
            entity_types: dict = {}
            for _, data in G.nodes(data=True):
                etype = data.get("entity_type", "UNKNOWN").replace('"', "")
                entity_types[etype] = entity_types.get(etype, 0) + 1

            return {
                "available":    True,
                "graph_name":   settings.MMKG_NAME,
                "nodes":        G.number_of_nodes(),
                "edges":        G.number_of_edges(),
                "entity_types": entity_types,
            }
        except Exception as exc:
            logger.warning(f"Could not read graph for summary: {exc}")
            return {"available": False, "error": str(exc)}
