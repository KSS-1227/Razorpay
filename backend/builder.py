"""
Pipeline orchestrator — wires all stages together.

Supports multi-format ingestion:
  .pdf                          → PdfChunking
  .docx                         → DocxChunking
  .xlsx / .xls                  → ExcelChunking
  .mp3 / .wav / .m4a / .flac   → AudioChunking
  .png / .jpg / .jpeg / .bmp /
  .webp / .tif / .tiff          → ImageChunking

All processors expose the same interface:
    texts, images = await processor.process()

Everything downstream (TextChunking → Graph → Fusion → Output) is unchanged.
"""
import hashlib
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import settings as parameter
from .graph.fusion import fusion
from .graph.img2graph import img2graph
from .graph.text2graph import TextEntityExtractor
from .ingestion.audio_preprocessing import AudioChunking
from .ingestion.csv_preprocessing import CSVChunking
from .ingestion.docx_preprocessing import DocxChunking
from .ingestion.excel_preprocessing import ExcelChunking
from .ingestion.image_preprocessing import ImageChunking
from .ingestion.pdf_preprocessing import PdfChunking, TextChunking
from .utils.base import get_latest_graphml_file, load_json, logger, write_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_cache_path = parameter.CACHE_PATH or "data/cache"
os.makedirs(_cache_path, exist_ok=True)
os.environ["CACHE_PATH"] = _cache_path

# ---------------------------------------------------------------------------
# Extension → processor mapping
# ---------------------------------------------------------------------------

_PDF_EXTS   = {".pdf"}
_DOCX_EXTS  = {".docx"}
_EXCEL_EXTS = {".xlsx", ".xls"}
_CSV_EXTS   = {".csv"}
_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}

_SUPPORTED_EXTS = _PDF_EXTS | _DOCX_EXTS | _EXCEL_EXTS | _CSV_EXTS | _AUDIO_EXTS | _IMAGE_EXTS


def _build_processor(file_path: str, working_dir: str, use_mineru: bool):
    """
    Return the correct preprocessing instance for *file_path*.

    All returned objects expose:  async process() -> (texts, images)
    """
    ext = Path(file_path).suffix.lower()

    if ext in _PDF_EXTS:
        return PdfChunking(
            pdf_path=file_path,
            working_dir=working_dir,
            use_mineru=use_mineru,
        )
    if ext in _DOCX_EXTS:
        return DocxChunking(
            docx_path=file_path,
            working_dir=working_dir,
        )
    if ext in _EXCEL_EXTS:
        return ExcelChunking(
            excel_path=file_path,
            working_dir=working_dir,
        )
    if ext in _CSV_EXTS:
        return CSVChunking(
            csv_path=file_path,
            working_dir=working_dir,
        )
    if ext in _AUDIO_EXTS:
        return AudioChunking(
            audio_path=file_path,
            working_dir=working_dir,
        )
    if ext in _IMAGE_EXTS:
        return ImageChunking(
            image_path=file_path,
            working_dir=working_dir,
        )

    raise ValueError(
        f"Unsupported file type '{ext}'. "
        f"Supported: {', '.join(sorted(_SUPPORTED_EXTS))}"
    )


@dataclass
class MMKGBuilder:
    file_path:   str  = field(default_factory=lambda: parameter.INPUT_PDF_PATH)
    working_dir: str  = field(default_factory=lambda: parameter.WORKING_DIR)
    output_dir:  str  = field(default_factory=lambda: parameter.OUTPUT_DIR)
    mmkg_name:   str  = field(default_factory=lambda: parameter.MMKG_NAME)
    use_mineru:  bool = field(default_factory=lambda: parameter.USE_MINERU)
    workspace_id: str | None = None

    def __post_init__(self):
        os.makedirs(self.working_dir, exist_ok=True)
        os.makedirs(self.output_dir,  exist_ok=True)
        os.makedirs(_cache_path,      exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def index(self, file_path: str | None = None):
        file_path = file_path or self.file_path
        logger.info(f"📂 Starting processing: {file_path}")

        if self._is_already_processed(file_path):
            logger.info(
                f"⏭️  '{Path(file_path).name}' was already indexed in this "
                f"session — skipping re-processing, graph is unchanged"
            )
            return

        await self._step_preprocessing(file_path)
        await self._step_text_extraction()
        img_ids = await self._step_image_extraction()
        await self._step_fusion(img_ids)
        await self._step_sync_graph_snapshot()
        await self._step_embeddings()
        self._step_save_output()
        self._step_generate_report()

        self._mark_processed(file_path)
        logger.info("✅ Knowledge graph build complete")

    # ------------------------------------------------------------------
    # Document-level tracking
    #
    # This replaces the old "does kv_store_text_chunks.json exist yet"
    # check. That check answered "has ANYTHING ever been indexed in this
    # working_dir", which meant document #2, #3, ... were silently
    # skipped in full. This answers "has THIS specific file already been
    # indexed", keyed by content hash — so re-uploading the exact same
    # file is still a safe no-op, but a genuinely new file always runs.
    # ------------------------------------------------------------------

    def _manifest_path(self) -> str:
        return os.path.join(self.working_dir, "processed_documents.json")

    @staticmethod
    def _file_hash(file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(1 << 16), b""):
                hasher.update(block)
        return hasher.hexdigest()

    def _is_already_processed(self, file_path: str) -> bool:
        manifest = load_json(self._manifest_path()) or {}
        return self._file_hash(file_path) in manifest

    def _mark_processed(self, file_path: str):
        manifest = load_json(self._manifest_path()) or {}
        manifest[self._file_hash(file_path)] = {
            "file_name": Path(file_path).name,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(manifest, self._manifest_path())

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    async def _step_preprocessing(self, file_path: str):
        # No existence check here anymore. TextChunking.text_chunking()
        # already hashes each doc/chunk's content (compute_mdhash_id) and
        # only inserts genuinely new content via filter_keys() against the
        # existing JsonKVStorage — see ingestion/pdf_preprocessing.py. It
        # was always safe to call on every upload; the old guard above it
        # was the actual bug, not this step.
        ext = Path(file_path).suffix.lower()
        logger.info(f"📄 Step 1/5 — File preprocessing [{ext}] for {Path(file_path).name}")

        processor = _build_processor(file_path, self.working_dir, self.use_mineru)
        texts, _images = await processor.process()

        text_chunking = TextChunking(working_dir=self.working_dir)
        await text_chunking.text_chunking(texts, file_name=Path(file_path).name)

    async def _step_text_extraction(self):
        logger.info("📝 Step 2/5 — Text entity extraction")

        chunks = load_json(os.path.join(self.working_dir, "kv_store_text_chunks.json")) or {}
        if not chunks:
            logger.info("⏭️  No text chunks available, skipping extraction")
            return

        # Track which chunk_ids have already been through LLM extraction,
        # separately from the "graph file exists" check that used to gate
        # this whole step. On a second document, `chunks` now contains
        # both old and new chunks (TextChunking accumulates them) — only
        # feed the genuinely new ones to the LLM extractor.
        extracted_path = os.path.join(self.working_dir, "kv_store_extracted_chunks.json")
        extracted_ids  = set(load_json(extracted_path) or [])

        new_chunks = {cid: c for cid, c in chunks.items() if cid not in extracted_ids}
        if not new_chunks:
            logger.info("⏭️  All chunks already extracted, skipping")
            return

        logger.info(
            f"🔍 Extracting entities from {len(new_chunks)} new chunk(s) "
            f"({len(chunks) - len(new_chunks)} already extracted previously)"
        )

        # NetworkXStorage.__post_init__ (storage/graph_storage.py) loads
        # the existing graph_chunk_entity_relation.graphml from disk
        # automatically if it's already there. So extractor.graph starts
        # from the PREVIOUS document's graph, and extract_entities()
        # upserts the new entities/edges into it — passing only new_chunks
        # here is what makes this an incremental merge instead of a
        # from-scratch rebuild.
        extractor = TextEntityExtractor(
            working_dir=self.working_dir,
            cache_dir=_cache_path,
            workspace_id=self.workspace_id,
        )
        await extractor.text_entity_extraction(new_chunks)

        extracted_ids.update(new_chunks.keys())
        write_json(list(extracted_ids), extracted_path)

    async def _step_image_extraction(self) -> list[str]:
        image_data_path = os.path.join(self.working_dir, "kv_store_image_data.json")
        image_data      = load_json(image_data_path) or {}
        img_ids         = list(image_data.keys())

        if not img_ids:
            logger.info("⏭️  No images found, skipping image extraction")
            return []

        logger.info(f"🖼️  Step 3/5 — Image entity extraction ({len(img_ids)} images)")
        images_dir = os.path.join(self.working_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        # Collect source images into images_dir
        image_paths = []
        for img_info in image_data.values():
            img_path = img_info.get("image_path", "")
            if os.path.exists(img_path):
                image_paths.append(img_path)

        if image_paths:
            # Run img2graph on the directory containing source images
            src_dir = os.path.dirname(image_paths[0])
            await img2graph(src_dir, working_dir=self.working_dir)

        return img_ids

    async def _step_fusion(self, img_ids: list[str]):
        if not img_ids:
            return

        # fusion() (graph/fusion.py) already loops per image_name and skips
        # only the images that already have their own graph_merged_{name}
        # .graphml on disk — that per-image check is correct and granular.
        # The blanket check that used to live here ("does ANY merged file
        # exist anywhere in working_dir") short-circuited fusion entirely
        # the moment a single image had ever been fused, which meant a
        # second document's images were never fused in at all. Just call
        # fusion() every time and let its own per-image guard do the work.
        logger.info(f"🔗 Step 4/5 — Graph fusion ({len(img_ids)} image(s) to check)")
        await fusion(img_ids, working_dir=self.working_dir)

    async def _step_sync_graph_snapshot(self):
        """Make CockroachDB authoritative again after local GraphML fusion."""
        if not self.workspace_id:
            return
        _namespace, graph_path = get_latest_graphml_file(self.working_dir)
        if not os.path.exists(graph_path):
            logger.warning("No GraphML snapshot available to sync to CockroachDB")
            return
        from .cockroach_graph_storage import CockroachGraphStorage

        storage = CockroachGraphStorage(
            namespace="chunk_entity_relation",
            storage_dir=self.working_dir,
            workspace_id=self.workspace_id,
        )
        await storage.replace_from_graphml(graph_path)

    async def _step_embeddings(self):
        # Skips silently in local-only mode (no workspace_id, i.e. still on
        # NetworkXStorage) — this step only applies once CockroachGraphStorage
        # is wired in, since it reads entities out of graph_nodes rows.
        if not self.workspace_id:
            return

        from . import cockroach_vector_storage as vector_store

        pending = await vector_store.nodes_missing_embeddings(self.workspace_id)
        if not pending:
            logger.info("⏭️  No new entities need embeddings")
            return

        logger.info(f"🧬 Step 5c/5 — Embedding {len(pending)} new entit{'y' if len(pending)==1 else 'ies'}")

        embed_model = parameter.get_embed_model()
        node_ids     = [nid for nid, _ in pending]
        descriptions = [desc for _, desc in pending]
        vectors      = embed_model.encode(descriptions)

        for node_id, vector in zip(node_ids, vectors):
            await vector_store.upsert_embedding(self.workspace_id, node_id, vector)

    def _step_save_output(self):
        logger.info("💾 Step 5a/5 — Saving final graph")
        _namespace, src_path = get_latest_graphml_file(self.working_dir)
        if not os.path.exists(src_path):
            logger.warning(f"⚠️  Graph file not found: {src_path}")
            return
        dest = os.path.join(self.output_dir, f"{self.mmkg_name}.graphml")
        shutil.copy2(src_path, dest)
        logger.info(f"📦 Graph saved to: {dest}")

    def _step_generate_report(self):
        logger.info("📊 Step 5b/5 — Generating report")
        import networkx as nx
        graph_path = os.path.join(self.output_dir, f"{self.mmkg_name}.graphml")
        if not os.path.exists(graph_path):
            return
        G = nx.read_graphml(graph_path)
        type_counts: dict = {}
        for _, data in G.nodes(data=True):
            etype = data.get("entity_type", "UNKNOWN").strip('"')
            type_counts[etype] = type_counts.get(etype, 0) + 1

        report_lines = [
            f"# Knowledge Graph Build Report — {self.mmkg_name}\n",
            f"- **Nodes**: {G.number_of_nodes()}",
            f"- **Edges**: {G.number_of_edges()}",
            "\n## Entity Type Distribution\n",
        ] + [f"- {k}: {v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1])]

        report_path = os.path.join(self.output_dir, f"{self.mmkg_name}_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        logger.info(f"📋 Report saved to: {report_path}")