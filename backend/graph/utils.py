"""
Shared graph-construction helpers used by text2graph and img2graph.
"""
from collections import Counter

from ..config import settings as parameter
from ..core.prompt import GRAPH_FIELD_SEP, PROMPTS
from ..llm import model_if_cache
from ..storage.graph_storage import BaseGraphStorage
from ..utils.base import (
    clean_str,
    decode_tokens_by_tiktoken,
    encode_string_by_tiktoken,
    is_float_regex,
    logger,
    split_string_by_multi_markers,
)


async def _handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    if len(record_attributes) < 4 or record_attributes[0] != '"entity"':
        return None
    entity_name = clean_str(record_attributes[1].upper())
    if not entity_name.strip():
        return None
    entity_type = clean_str(record_attributes[2].upper())
    entity_description = clean_str(record_attributes[3])
    return {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "description": entity_description,
        "source_id":   chunk_key,
    }


async def _handle_entity_relation_summary(
    entity_or_relation_name: str,
    description: str,
) -> str:
    use_llm_func = model_if_cache
    llm_max_tokens = parameter.SUMMARY_CONTEXT_MAX_TOKENS
    summary_max_tokens = parameter.ENTITY_SUMMARY_MAX_TOKENS
    tokens = encode_string_by_tiktoken(description)
    if len(tokens) < summary_max_tokens:
        return description
    prompt_template = PROMPTS["summarize_entity_descriptions"]
    use_description = decode_tokens_by_tiktoken(tokens[:llm_max_tokens])
    context_base = {
        "entity_name":      entity_or_relation_name,
        "description_list": use_description.split(GRAPH_FIELD_SEP),
    }
    user_prompt = prompt_template.format(**context_base)
    logger.debug(f"Trigger summary: {entity_or_relation_name}")
    return await use_llm_func(user_prompt, max_tokens=summary_max_tokens)


async def _handle_single_relationship_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    if len(record_attributes) < 5 or record_attributes[0] != '"relationship"':
        return None
    source = clean_str(record_attributes[1].upper())
    target = clean_str(record_attributes[2].upper())
    edge_description = clean_str(record_attributes[3])
    weight = (
        float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 1.0
    )
    return {
        "src_id":      source,
        "tgt_id":      target,
        "weight":      weight,
        "description": edge_description,
        "source_id":   chunk_key,
    }


async def _merge_nodes_then_upsert(
    entity_name: str,
    nodes_data: list[dict],
    knwoledge_graph_inst: BaseGraphStorage,
):
    already_entitiy_types = []
    already_source_ids = []
    already_description = []
    already_node = await knwoledge_graph_inst.get_node(entity_name)
    if already_node is not None:
        already_entitiy_types.append(already_node["entity_type"])
        already_source_ids.extend(
            split_string_by_multi_markers(already_node["source_id"], [GRAPH_FIELD_SEP])
        )
        already_description.append(already_node["description"])
    entity_type = max(
        Counter(
            [dp["entity_type"] for dp in nodes_data] + already_entitiy_types
        ).items(),
        key=lambda x: x[1],
    )[0]
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in nodes_data] + already_description))
    )
    source_id = GRAPH_FIELD_SEP.join(
        set([dp["source_id"] for dp in nodes_data] + already_source_ids)
    )
    description = await _handle_entity_relation_summary(entity_name, description)
    node_data = {"entity_type": entity_type, "description": description, "source_id": source_id}
    await knwoledge_graph_inst.upsert_node(entity_name, node_data=node_data)
    node_data["entity_name"] = entity_name
    return node_data


async def _merge_edges_then_upsert(
    src_id: str,
    tgt_id: str,
    edges_data: list[dict],
    knwoledge_graph_inst: BaseGraphStorage,
):
    already_weights = []
    already_source_ids = []
    already_description = []
    already_order = []
    if await knwoledge_graph_inst.has_edge(src_id, tgt_id):
        already_edge = await knwoledge_graph_inst.get_edge(src_id, tgt_id)
        already_weights.append(already_edge["weight"])
        already_source_ids.extend(
            split_string_by_multi_markers(already_edge["source_id"], [GRAPH_FIELD_SEP])
        )
        already_description.append(already_edge["description"])
        already_order.append(already_edge.get("order", 1))
    order = min([dp.get("order", 1) for dp in edges_data] + already_order)
    weight = sum([dp["weight"] for dp in edges_data] + already_weights)
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in edges_data] + already_description))
    )
    source_id = GRAPH_FIELD_SEP.join(
        set([dp["source_id"] for dp in edges_data] + already_source_ids)
    )
    for need_insert_id in [src_id, tgt_id]:
        if not (await knwoledge_graph_inst.has_node(need_insert_id)):
            await knwoledge_graph_inst.upsert_node(
                need_insert_id,
                node_data={
                    "source_id": source_id,
                    "description": description,
                    "entity_type": '"UNKNOWN"',
                },
            )
    description = await _handle_entity_relation_summary((src_id, tgt_id), description)
    await knwoledge_graph_inst.upsert_edge(
        src_id,
        tgt_id,
        edge_data={
            "weight": weight,
            "description": description,
            "source_id": source_id,
            "order": order,
        },
    )
