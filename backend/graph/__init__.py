"""
Graph construction package.
"""
from .fusion import fusion
from .img2graph import ImageEntityExtractor, img2graph
from .text2graph import TextEntityExtractor, extract_entities
from .utils import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction,
    _merge_edges_then_upsert,
    _merge_nodes_then_upsert,
)

__all__ = [
    "ImageEntityExtractor",
    "TextEntityExtractor",
    "_handle_single_entity_extraction",
    "_handle_single_relationship_extraction",
    "_merge_edges_then_upsert",
    "_merge_nodes_then_upsert",
    "extract_entities",
    "fusion",
    "img2graph",
]
