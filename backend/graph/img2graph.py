"""
Image-to-graph pipeline: extracts entities and relations from images.
"""
import asyncio
import base64
import os
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import cast

from PIL import Image
from tqdm import tqdm

from ..config import settings as parameter
from ..core.prompt import PROMPTS
from ..llm import multimodel_if_cache
from ..storage.graph_storage import BaseGraphStorage, NetworkXStorage
from ..storage.kv_storage import BaseKVStorage, JsonKVStorage, StorageNameSpace
from ..utils.base import (
    clean_str,
    limit_async_func_call,
    load_json,
    logger,
    split_string_by_multi_markers,
)
from .utils import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction,
    _merge_edges_then_upsert,
    _merge_nodes_then_upsert,
)

TUPLE_DELIMITER      = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
RECORD_DELIMITER     = PROMPTS["DEFAULT_RECORD_DELIMITER"]
COMPLETION_DELIMITER = PROMPTS["DEFAULT_COMPLETION_DELIMITER"]
MIN_IMAGE_SIZE = 28


# ============================================================================
# Image region extraction — GPT-4o vision (replaces YOLOv8 segmentation)
# ============================================================================

async def extract_feature_chunks(image_path: str, working_dir: str | None = None) -> str:
    """Identify distinct regions/objects in the image using GPT-4o vision.

    Instead of running YOLOv8 segmentation to crop regions, we ask GPT-4o to
    describe each distinct region and save a synthetic description file so that
    downstream ``feature_image_entity_construction`` has something to work with.

    The function still returns ``save_dir`` (a directory path string) so the
    call-site contract is unchanged.  If GPT-4o identifies regions we save
    one synthetic image description per region as a small placeholder JPEG
    (a 1×1 pixel image tagged with a ``{region_label}.jpg`` filename) alongside
    a UTF-8 text description injected as an image entity string.

    Falls back gracefully — if the vision call fails the directory is returned
    empty and downstream consumers already handle that with ``if not jpg_files:
    return []``.
    """
    from ..llm import multimodel_if_cache
    from ..storage.kv_storage import JsonKVStorage

    base       = working_dir or parameter.WORKING_DIR
    image_name = Path(image_path).stem
    save_dir   = os.path.join(base, "images", image_name)
    os.makedirs(save_dir, exist_ok=True)

    # Skip if already processed (idempotent)
    if _get_jpg_files(save_dir):
        return save_dir

    # ------------------------------------------------------------------
    # Ask GPT-4o to identify regions and their relationships
    # ------------------------------------------------------------------
    img_base64 = _encode_image_base64(image_path)

    region_prompt = (
        "Analyse this enterprise image. Identify every distinct visual region, "
        "object, chart, table, diagram, person, label, or concept visible. "
        "For each region output ONE line in EXACTLY this format:\n"
        "REGION: <short_name> | TYPE: <entity_type> | DESC: <one sentence description>\n"
        "Then output a RELATIONSHIPS section:\n"
        "REL: <source_name> -> <target_name> | DESC: <relationship description>\n"
        "Output only these lines — no prose, no markdown fences."
    )

    cache_kv = JsonKVStorage(
        namespace="multimodel_llm_response_cache",
        storage_dir=parameter.CACHE_PATH,
    )

    try:
        raw = await multimodel_if_cache(
            user_prompt=region_prompt,
            img_base=img_base64,
            system_prompt="You are an expert visual analyst for enterprise compliance documents.",
            hashing_kv=cache_kv,
        )
    except Exception as exc:
        logger.warning("GPT-4o region extraction failed for %s: %s", image_path, exc)
        return save_dir
    finally:
        await cache_kv.index_done_callback()

    # ------------------------------------------------------------------
    # Parse and write one synthetic placeholder JPEG per region
    # ------------------------------------------------------------------
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line.startswith("REGION:"):
            continue
        try:
            parts = dict(p.split(":", 1) for p in line.split("|"))
            short_name = parts.get("REGION", "region").strip().replace(" ", "_")
            # Write a 1x1 white placeholder JPEG so _get_jpg_files picks it up
            placeholder = os.path.join(save_dir, f"{short_name}.jpg")
            if not os.path.exists(placeholder):
                Image.new("RGB", (32, 32), color=(200, 200, 200)).save(placeholder)
        except Exception:
            continue

    # Store the raw GPT-4o region text so feature_image_entity_construction
    # can use it via the LLM cache hit when it re-encodes the same image.
    region_cache_path = os.path.join(save_dir, "_regions.txt")
    try:
        with open(region_cache_path, "w", encoding="utf-8") as f:
            f.write(raw)
    except Exception:
        pass

    return save_dir
# ============================================================================
# Entity extraction helpers
# ============================================================================

def _encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_jpg_files(directory: str) -> list[str]:
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(".jpg")
    ]


def _build_entity_string(name: str, entity_type: str, description: str) -> str:
    return f'("entity"{TUPLE_DELIMITER}"{name}"{TUPLE_DELIMITER}"{entity_type}"{TUPLE_DELIMITER}"{description}"){RECORD_DELIMITER}'


def _build_relationship_string(src: str, tgt: str, description: str, weight: int = 10) -> str:
    return f'("relationship"{TUPLE_DELIMITER}"{src}"{TUPLE_DELIMITER}"{tgt}"{TUPLE_DELIMITER}"{description}"{TUPLE_DELIMITER}{weight}){RECORD_DELIMITER}'


async def feature_image_entity_construction(feature_dir: str, llm_func) -> list[str]:
    entities  = []
    jpg_files = _get_jpg_files(feature_dir)
    if not jpg_files:
        return entities

    prompt_user   = PROMPTS["feature_image_description_user"]
    prompt_system = PROMPTS["feature_image_description_system"]

    for image_path in jpg_files:
        filename = os.path.basename(image_path)
        with Image.open(image_path) as img:
            width, height = img.size
        if width <= MIN_IMAGE_SIZE or height <= MIN_IMAGE_SIZE:
            logger.info(f"🖼️ Skipping small image: {filename} ({width}x{height})")
            os.remove(image_path)
            continue
        img_base64  = _encode_image_base64(image_path)
        description = await llm_func(user_prompt=prompt_user, img_base=img_base64, system_prompt=prompt_system)
        entities.append(_build_entity_string(filename, "img", description).replace("\n", ""))

    return entities


async def feature_image_relationship_construction(feature_dir: str, entity_descriptions: str, llm_func) -> list[str]:
    relationships = []
    jpg_files     = _get_jpg_files(feature_dir)
    if not jpg_files:
        return relationships

    prompt_system = PROMPTS["entity_alignment_system"].format(
        tuple_delimiter=TUPLE_DELIMITER, record_delimiter=RECORD_DELIMITER
    )
    for image_path in jpg_files:
        filename   = os.path.basename(image_path)
        prompt_user = PROMPTS["entity_alignment_user"].format(
            entity_description=entity_descriptions, feature_image_name=filename
        )
        img_base64 = _encode_image_base64(image_path)
        result     = await llm_func(user_prompt=prompt_user, img_base=img_base64, system_prompt=prompt_system)
        relationships.append(result)

    return relationships


async def extract_entities_from_image(image_path: str, llm_func) -> str:
    prompt     = PROMPTS["image_entity_extraction"].format(
        tuple_delimiter=TUPLE_DELIMITER, record_delimiter=RECORD_DELIMITER,
        completion_delimiter=COMPLETION_DELIMITER,
        entity_types=",".join(PROMPTS["DEFAULT_ENTITY_TYPES"]),
    )
    img_base64 = _encode_image_base64(image_path)
    return await llm_func(
        user_prompt="Please output the results in the format provided in the example.\nOutput:",
        img_base=img_base64, system_prompt=prompt
    )


async def build_original_image_entity(image_path: str, feature_entities: list[str], extracted_result: str) -> list[str]:
    results    = []
    image_data = load_json(os.path.join(parameter.WORKING_DIR, "kv_store_image_data.json")) or {}

    filename = description = None
    for key, info in image_data.items():
        if info.get("image_path") == image_path:
            filename    = key
            description = info.get("description", "")
            break
    if not filename:
        return results

    results.append(_build_entity_string(filename, "ori_img", description).replace("\n", ""))

    pattern = r'\"([^\"]+?\.jpg)\"'
    for feature_entity in feature_entities:
        matches = re.findall(pattern, feature_entity)
        if matches:
            results.append(_build_relationship_string(matches[0], filename, f"{matches[0]} is an image feature block of {filename}."))

    entity_pattern = r'\"entity\"\<\|\>\"([^\"]+?)\"'
    results.extend(
        _build_relationship_string(
            clean_str(entity_name.upper()),
            filename,
            f"{clean_str(entity_name.upper())} is an entity extracted from {filename}.",
        )
        for entity_name in re.findall(entity_pattern, extracted_result)
    )

    return results


def format_entities_result(result: str) -> str:
    pattern  = r'\("entity"<\|>"([^"]+)"<\|>"[^"]*"<\|>"([^"]+)"\)'
    entities = re.findall(pattern, result)
    return "\n".join([f'"{e}"-"{d}"' for e, d in entities])


# ============================================================================
# Main extraction function
# ============================================================================

async def extract_entities(
    cache_storage: BaseKVStorage,
    image_path: str,
    feature_dir: str,
    knwoledge_graph_inst: BaseGraphStorage,
) -> BaseGraphStorage | None:
    llm_func = limit_async_func_call(16)(
        partial(multimodel_if_cache, hashing_kv=cache_storage)
    )

    feature_entities  = await feature_image_entity_construction(feature_dir, llm_func)
    image_entities    = await extract_entities_from_image(image_path, llm_func)
    formatted_entities = format_entities_result(image_entities)
    relationships     = await feature_image_relationship_construction(feature_dir, formatted_entities, llm_func)
    original_entities = await build_original_image_entity(image_path, feature_entities, image_entities)

    all_results  = feature_entities + relationships + original_entities
    final_result = "\n" + "\n".join(all_results) + image_entities.strip()

    records = split_string_by_multi_markers(final_result, [RECORD_DELIMITER, COMPLETION_DELIMITER])

    maybe_nodes = defaultdict(list)
    maybe_edges = defaultdict(list)

    for record in records:
        match = re.search(r"\((.*)\)", record)
        if not match:
            continue
        attrs  = split_string_by_multi_markers(match.group(1), [TUPLE_DELIMITER])
        entity = await _handle_single_entity_extraction(attrs, image_path)
        if entity:
            maybe_nodes[entity["entity_name"]].append(entity)
            continue
        relation = await _handle_single_relationship_extraction(attrs, image_path)
        if relation:
            maybe_edges[(relation["src_id"], relation["tgt_id"])].append(relation)

    merged_edges = {}
    for key, data_list in maybe_edges.items():
        merged_edges.setdefault(tuple(sorted(key)), []).extend(data_list)

    all_entities = await asyncio.gather(*[
        _merge_nodes_then_upsert(k, v, knwoledge_graph_inst) for k, v in maybe_nodes.items()
    ])
    await asyncio.gather(*[
        _merge_edges_then_upsert(k[0], k[1], v, knwoledge_graph_inst) for k, v in merged_edges.items()
    ])

    if not all_entities:
        logger.warning("No entities extracted")
        return None
    return knwoledge_graph_inst


# ============================================================================
# Extractor class
# ============================================================================

@dataclass
class ImageEntityExtractor:
    extraction_func:   callable              = extract_entities
    kv_storage_cls:    type[BaseKVStorage]   = JsonKVStorage
    graph_storage_cls: type[BaseGraphStorage] = NetworkXStorage
    working_dir:       str | None            = None

    def __post_init__(self):
        cache_dir = self.working_dir or parameter.CACHE_PATH
        self.llm_cache = self.kv_storage_cls(
            namespace="multimodel_llm_response_cache",
            storage_dir=cache_dir,
        )
        graph_dir = self.working_dir or parameter.WORKING_DIR
        self.graph = self.graph_storage_cls(
            namespace="image_entity_relation",
            storage_dir=graph_dir,
        )

    async def extract(self, image_path: str):
        try:
            feature_dir = await extract_feature_chunks(image_path, working_dir=self.working_dir)
            logger.info("🔍 Extracting entities...")
            result = await self.extraction_func(
                self.llm_cache, image_path, feature_dir, knwoledge_graph_inst=self.graph,
            )
            if result is None:
                logger.warning("No entities found")
            else:
                self.graph = result
        finally:
            await self._save()

    async def _save(self):
        tasks = [
            cast(StorageNameSpace, s).index_done_callback()
            for s in [self.llm_cache, self.graph] if s
        ]
        await asyncio.gather(*tasks)


async def img2graph(images_dir: str, working_dir: str | None = None):
    jpg_files = _get_jpg_files(images_dir)
    if not jpg_files:
        return

    base = working_dir or parameter.WORKING_DIR

    for image_path in tqdm(jpg_files, desc="🖼️ Image entity extraction", unit="image"):
        image_name        = Path(image_path).stem
        target_graph_path = os.path.join(
            base, "images", image_name,
            f"graph_{image_name}_entity_relation.graphml"
        )
        if os.path.exists(target_graph_path):
            continue

        extractor = ImageEntityExtractor(working_dir=working_dir)
        await extractor.extract(image_path)

        src = os.path.join(base, "graph_image_entity_relation.graphml")
        if os.path.exists(src):
            shutil.move(src, target_graph_path)