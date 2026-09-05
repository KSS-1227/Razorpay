"""
Document Service

Acts as a thin wrapper around MMKGBuilder.

Responsibilities:
-----------------
1. Validate uploaded file exists
2. Invoke MMKGBuilder (format-aware — supports pdf, docx, xlsx, audio, images)
3. Read generated GraphML
4. Compute graph statistics
5. Return metadata to API
"""

import time
import uuid
from pathlib import Path

import networkx as nx

from backend.builder import _SUPPORTED_EXTS, MMKGBuilder
from backend.config import settings


class DocumentService:

    def __init__(self):
        # The builder is created per document after a stable workspace ID is
        # available; CockroachGraphStorage requires that scope.
        self.builder: MMKGBuilder | None = None

    async def process_document(
        self,
        file_path: str,
        original_filename: str,
        file_id: str | None = None,
    ):
        start_time = time.time()
        file_id    = file_id or str(uuid.uuid4())
        path       = Path(file_path)

        self.builder = MMKGBuilder(workspace_id=file_id)

        if not path.exists():
            raise FileNotFoundError(file_path)

        extension = path.suffix.lower()

        if extension not in _SUPPORTED_EXTS:
            raise ValueError(
                f"Unsupported file type '{extension}'. "
                f"Supported: {', '.join(sorted(_SUPPORTED_EXTS))}"
            )

        # -------------------------------------------------------
        # Build Knowledge Graph
        # -------------------------------------------------------

        await self.builder.index(str(path))

        graph_path = (
            Path(settings.OUTPUT_DIR) / f"{settings.MMKG_NAME}.graphml"
        )

        if not graph_path.exists():
            raise RuntimeError("GraphML file was not generated.")

        graph        = nx.read_graphml(graph_path)
        entity_types = {}
        for _, data in graph.nodes(data=True):
            entity = data.get("entity_type", "UNKNOWN").replace('"', "")
            entity_types[entity] = entity_types.get(entity, 0) + 1

        processing_time = round(time.time() - start_time, 2)

        report_path = (
            Path(settings.OUTPUT_DIR) / f"{settings.MMKG_NAME}_report.md"
        )

        return {
            "document": {
                "id":      file_id,
                "name":    original_filename,
                "type":    extension,
                "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
            },
            "knowledge_graph": {
                "graph_name":   settings.MMKG_NAME,
                "graph_path":   str(graph_path),
                "nodes":        graph.number_of_nodes(),
                "edges":        graph.number_of_edges(),
                "entity_types": entity_types,
            },
            "report": {
                "available": report_path.exists(),
                "path":      str(report_path),
            },
            "processing": {
                "status":       "completed",
                "time_seconds": processing_time,
            },
        }
