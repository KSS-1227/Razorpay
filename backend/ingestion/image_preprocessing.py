"""
Image preprocessing pipeline.

Enterprise Compliance Intelligence Platform

Purpose
-------
Process standalone enterprise images into the MMGraphRAG pipeline.

Supported Formats
-----------------
- png, jpg, jpeg, bmp, webp, tif, tiff

Output
------
texts  : List[str]
images : List[dict]

Unlike PdfChunking, this module starts from a standalone image instead of
extracting images from a PDF.  The generated description becomes input to
TextChunking while image metadata is preserved for multimodal retrieval.
"""

from __future__ import annotations

import os

from ..utils.base import logger
from .image_utils import copy_image_to_working_dir, describe_image_sync


class ImageChunking:

    def __init__(
        self,
        image_path: str,
        working_dir: str,
    ):
        self.image_path  = image_path
        self.working_dir = working_dir
        self.images_dir  = os.path.join(working_dir, "images")

    # ------------------------------------------------------------------
    # Public entry
    # ------------------------------------------------------------------

    async def process(self) -> tuple[list[str], list[dict]]:
        logger.info("🖼 Processing standalone image...")

        image_info = copy_image_to_working_dir(
            self.image_path,
            self.images_dir,
        )

        description = describe_image_sync(image_info["image_path"])

        image_info["description"] = description

        logger.info("✅ Image preprocessing completed.")

        return [description], [image_info]
