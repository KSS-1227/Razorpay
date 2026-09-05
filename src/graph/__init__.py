"""
图谱构建模块

包含文本实体提取、图像实体提取、图谱融合等功能。
"""
from .text2graph import TextEntityExtractor, extract_entities
from .img2graph import ImageEntityExtractor, img2graph
from .fusion import fusion
from .utils import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction,
    _merge_nodes_then_upsert,
    _merge_edges_then_upsert,
)

__all__ = [
    "TextEntityExtractor",
    "extract_entities",
    "ImageEntityExtractor",
    "img2graph",
    "fusion",
    "_handle_single_entity_extraction",
    "_handle_single_relationship_extraction",
    "_merge_nodes_then_upsert",
    "_merge_edges_then_upsert",
]
