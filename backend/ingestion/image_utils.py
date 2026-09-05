"""
Shared image utilities for the ingestion pipeline.

Used by:
  - pdf_preprocessing.py   (PdfChunking)
  - image_preprocessing.py (ImageChunking)

Rules
-----
- No new OpenAI / Vision client.  All LLM calls go through the existing
  MMGraphRAG pipeline: multimodel_if_cache (async) or get_mmllm_response (sync).
- No behaviour changes — functions are lifted verbatim from their original
  locations with only the import paths adjusted.
- All public names that existed before remain importable from their original
  modules (those modules now re-import from here).
"""

from __future__ import annotations

import asyncio
import base64
import os
import shutil

from PIL import Image

from ..core.prompt import PROMPTS
from ..llm import get_mmllm_response, multimodel_if_cache, normalize_to_json
from ..utils.base import logger

# ---------------------------------------------------------------------------
# compress_image_to_size
# ---------------------------------------------------------------------------

def compress_image_to_size(
    input_image: Image.Image,
    output_path: str,
    target_size_mb: float = 5,
    step: int = 10,
    quality: int = 90,
) -> bool:
    """
    Save a PIL image to *output_path*, re-encoding at lower quality until the
    file is under *target_size_mb*.  Returns True on success, False if the
    target could not be reached.
    """
    target_bytes = target_size_mb * 1024 * 1024
    input_image.save(output_path, quality=quality)
    while os.path.getsize(output_path) > target_bytes and quality > 10:
        quality -= step
        input_image.save(output_path, quality=quality)
    if os.path.getsize(output_path) <= target_bytes:
        return True
    logger.warning("⚠️ Unable to compress image to target size")
    return False


# ---------------------------------------------------------------------------
# encode_image_base64
# ---------------------------------------------------------------------------

def encode_image_base64(image_path: str) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# get_image_description  (async — used by PdfChunking)
# ---------------------------------------------------------------------------

async def get_image_description(
    image_path: str,
    caption: list,
    footnote: list,
    context: str,
    hashing_kv=None,
) -> tuple[str, bool]:
    """
    Call the multimodal LLM to describe an image extracted from a document.

    Returns
    -------
    description : str
    segmentation : bool   — True if YOLO segmentation is recommended
    """
    img_base64 = encode_image_base64(image_path)

    user_prompt = PROMPTS["image_description_user_with_examples"].format(
        caption=" ".join(caption),
        footnote=" ".join(footnote),
        context=context,
    )

    default_result: dict = {"description": "No description.", "segmentation": "false"}

    try:
        content = await asyncio.wait_for(
            multimodel_if_cache(
                user_prompt=user_prompt,
                img_base=img_base64,
                system_prompt=PROMPTS["image_description_system"],
                hashing_kv=hashing_kv,
            ),
            timeout=30.0,
        )
        result = normalize_to_json(content) or default_result
    except TimeoutError:
        logger.warning(f"⏱️ Image description timed out: {image_path}")
        result = {
            "description": "Image description generation timed out.",
            "segmentation": "false",
        }
    except Exception as e:
        logger.error(f"❌ Image description generation failed {image_path}: {e}")
        result = {
            "description": "Image description generation failed.",
            "segmentation": "false",
        }

    description  = result.get("description", "No description.")
    segmentation = str(result.get("segmentation", "false")).lower() == "true"
    return description, segmentation


# ---------------------------------------------------------------------------
# describe_image_sync  (sync — used by ImageChunking)
# ---------------------------------------------------------------------------

def describe_image_sync(image_path: str) -> str:
    """
    Call the multimodal LLM synchronously to describe a standalone image.

    Uses the existing get_mmllm_response (sync wrapper in llm/client.py).
    Falls back gracefully on any error.
    """
    img_base64 = encode_image_base64(image_path)

    prompt = PROMPTS.get(
        "image_description",
        (
            "Describe this enterprise image. "
            "Identify diagrams, controls, labels, "
            "equipment, tables, architecture, "
            "compliance evidence and all visible entities."
        ),
    )

    try:
        response = get_mmllm_response(
            cur_prompt=prompt,
            system_content=PROMPTS.get("image_description_system", "You are a helpful assistant."),
            img_base=img_base64,
        )
        return response.strip()
    except Exception as e:
        logger.error(f"❌ describe_image_sync failed for {image_path}: {e}")
        return "Image description generation failed."


# ---------------------------------------------------------------------------
# copy_image_to_working_dir
# ---------------------------------------------------------------------------

def copy_image_to_working_dir(
    image_path: str,
    images_dir: str,
) -> dict[str, str]:
    """
    Copy *image_path* into *images_dir* (no-op if already there).

    Returns a dict with ``image_name`` and ``image_path`` keys.
    """
    os.makedirs(images_dir, exist_ok=True)
    filename    = os.path.basename(image_path)
    destination = os.path.join(images_dir, filename)

    if os.path.abspath(image_path) != os.path.abspath(destination):
        shutil.copy2(image_path, destination)

    return {
        "image_name": filename,
        "image_path": destination,
    }


# ---------------------------------------------------------------------------
# find_chunk_for_image
# ---------------------------------------------------------------------------

def find_chunk_for_image(text_chunks: dict, context: str) -> str | None:
    """
    Find the text chunk whose content best overlaps with *context*.

    Returns the chunk_id string, or None if *context* is empty / no match.
    """
    if not context:
        return None

    best_chunk_id    = None
    best_match_count = 0
    context_words    = set(context.split())

    for chunk_id, chunk_data in text_chunks.items():
        chunk_content = chunk_data["content"].replace("\n", "")
        match_count   = sum(1 for word in context_words if word in chunk_content)
        if match_count > best_match_count:
            best_match_count = match_count
            best_chunk_id    = chunk_id

    return best_chunk_id
