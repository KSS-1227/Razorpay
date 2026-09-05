"""
图谱工具模块 - 提供图谱构建的公共函数

该模块包含用于处理实体和关系提取、合并节点和边的通用函数，
被 text2graph.py 和 img2graph.py 共同使用。
"""
from collections import Counter
from typing import Union

from ..core.prompt import GRAPH_FIELD_SEP, PROMPTS
from ..core.base import (
    logger,
    split_string_by_multi_markers,
    clean_str,
    encode_string_by_tiktoken,
    decode_tokens_by_tiktoken,
    is_float_regex,
)
from .. import parameter
from ..core.storage import BaseGraphStorage
from ..llm import model_if_cache


async def _handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    """
    处理单个实体提取任务。

    该函数负责验证并处理给定的实体记录属性，从中提取实体名称、类型和描述等信息，
    并返回一个字典，包含这些信息以及实体的来源标识。

    参数:
    - record_attributes: 一个字符串列表，包含实体的属性信息。预期列表中至少有4个元素，
      第一个元素为'entity'，标识这是一个实体记录。
    - chunk_key: 一个字符串，表示实体信息来源的唯一标识。

    返回:
    - 如果记录属性有效，返回一个字典，包含实体名称、类型、描述和来源标识。
    - 如果记录属性无效（如元素数量不足或第一个元素不是'entity'），则返回None。
    """
    # 检查record_attributes列表是否至少有4个元素，且第一个元素是否为'entity'
    if len(record_attributes) < 4 or record_attributes[0] != '"entity"':
        return None
    # add this record as a node in the G
    entity_name = clean_str(record_attributes[1].upper())
    if not entity_name.strip():
        return None
    entity_type = clean_str(record_attributes[2].upper())
    entity_description = clean_str(record_attributes[3])
    entity_source_id = chunk_key
    return dict(
        entity_name=entity_name,
        entity_type=entity_type,
        description=entity_description,
        source_id=entity_source_id,
    )


async def _handle_entity_relation_summary(
    entity_or_relation_name: str,
    description: str,
) -> str:
    """
    根据全局配置处理实体和关系的描述并生成摘要。

    参数:
    - entity_or_relation_name: 实体或关系的名称。
    - description: 实体或关系的描述。

    返回:
    - 生成的摘要或原始描述。
    """
    # 从参数模块获取配置
    use_llm_func = model_if_cache
    llm_max_tokens = parameter.SUMMARY_CONTEXT_MAX_TOKENS
    summary_max_tokens = parameter.ENTITY_SUMMARY_MAX_TOKENS
    # 编码描述信息
    tokens = encode_string_by_tiktoken(description)
    # 如果描述信息的令牌数小于最大摘要令牌数，则直接返回描述信息
    if len(tokens) < summary_max_tokens:  # No need for summary
        return description
    # 设置prompt
    prompt_template = PROMPTS["summarize_entity_descriptions"]
    # 获取适合模型最大令牌数的描述信息
    use_description = decode_tokens_by_tiktoken(
        tokens[:llm_max_tokens]
    )
    # 构建上下文基础信息
    context_base = dict(
        entity_name=entity_or_relation_name,
        description_list=use_description.split(GRAPH_FIELD_SEP),
    )
    # 构建最终的prompt
    user_prompt = prompt_template.format(**context_base)
    logger.debug(f"Trigger summary: {entity_or_relation_name}")
    # 使用语言模型生成摘要
    summary = await use_llm_func(user_prompt, max_tokens=summary_max_tokens)
    return summary


async def _handle_single_relationship_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    """
    处理单个关系提取任务。

    参数:
    - record_attributes: 一个字符串列表，包含关系的属性信息。
    - chunk_key: 关系来源的唯一标识。

    返回:
    - 如果记录属性有效，返回包含关系信息的字典，否则返回None。
    """
    if len(record_attributes) < 5 or record_attributes[0] != '"relationship"':
        return None
    # add this record as edge
    source = clean_str(record_attributes[1].upper())
    target = clean_str(record_attributes[2].upper())
    edge_description = clean_str(record_attributes[3])
    edge_source_id = chunk_key
    weight = (
        float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 1.0
    )
    return dict(
        src_id=source,
        tgt_id=target,
        weight=weight,
        description=edge_description,
        source_id=edge_source_id,
    )


async def _merge_nodes_then_upsert(
    entity_name: str,
    nodes_data: list[dict],
    knwoledge_graph_inst: BaseGraphStorage,
):
    """
    合并节点数据并更新或插入知识图谱中的节点。

    该函数首先尝试从知识图谱中获取已存在的节点信息，然后与新获取的节点数据进行合并。
    合并后的节点数据将根据给定的规则更新或插入到知识图谱中。

    参数:
    - entity_name (str): 实体名称，用于标识知识图谱中的节点。
    - nodes_data (list[dict]): 一组节点数据，每个节点数据是一个字典。
    - knwoledge_graph_inst (BaseGraphStorage): 知识图谱实例，用于操作知识图谱。

    返回:
    - node_data (dict): 更新或插入后的节点数据。
    """
    # 初始化列表，用于存储已存在的节点信息
    already_entitiy_types = []
    already_source_ids = []
    already_description = []
    # 从知识图谱中获取已存在的节点信息
    already_node = await knwoledge_graph_inst.get_node(entity_name)
    if already_node is not None:
        # 如果节点存在，则将已存在的信息添加到对应的列表中
        already_entitiy_types.append(already_node["entity_type"])
        already_source_ids.extend(
            split_string_by_multi_markers(already_node["source_id"], [GRAPH_FIELD_SEP])
        )
        already_description.append(already_node["description"])
    # 合并新旧节点的实体类型，选择出现次数最多的作为新的实体类型
    entity_type = sorted(
        Counter(
            [dp["entity_type"] for dp in nodes_data] + already_entitiy_types
        ).items(),
        key=lambda x: x[1],
        reverse=True,
    )[0][0]
    # 合并新旧节点的描述，使用分隔符连接所有不同的描述
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in nodes_data] + already_description))
    )
    # 合并新旧节点的源ID，使用分隔符连接所有不同的源ID
    source_id = GRAPH_FIELD_SEP.join(
        set([dp["source_id"] for dp in nodes_data] + already_source_ids)
    )
    # 处理实体的描述信息
    description = await _handle_entity_relation_summary(
        entity_name, description
    )
    node_data = dict(
        entity_type=entity_type,
        description=description,
        source_id=source_id,
    )
    # 更新或插入节点到知识图谱
    await knwoledge_graph_inst.upsert_node(
        entity_name,
        node_data=node_data,
    )
    # 添加实体名称到节点数据中
    node_data["entity_name"] = entity_name
    return node_data


async def _merge_edges_then_upsert(
    src_id: str,
    tgt_id: str,
    edges_data: list[dict],
    knwoledge_graph_inst: BaseGraphStorage,
):
    """
    合并边数据并插入/更新知识图谱。
    该函数检查src_id和tgt_id之间是否存在边，如果存在，则获取当前边数据并
    与新的边数据(edges_data)合并；如果不存在，则直接插入新的边数据。同时，
    如果src_id或tgt_id在图中不存在相应的节点，则插入默认属性的节点。

    参数:
    - src_id (str): 边的起始节点ID。
    - tgt_id (str): 边的目标节点ID。
    - edges_data (list[dict]): 包含一个或多个边的数据。
    - knwoledge_graph_inst (BaseGraphStorage): 知识图谱实例。
    """
    already_weights = []
    already_source_ids = []
    already_description = []
    already_order = []
    # 如果src_id和tgt_id之间存在边，则获取现有边数据
    if await knwoledge_graph_inst.has_edge(src_id, tgt_id):
        already_edge = await knwoledge_graph_inst.get_edge(src_id, tgt_id)
        already_weights.append(already_edge["weight"])
        already_source_ids.extend(
            split_string_by_multi_markers(already_edge["source_id"], [GRAPH_FIELD_SEP])
        )
        already_description.append(already_edge["description"])
        already_order.append(already_edge.get("order", 1))

    # [numberchiffre]: `Relationship.order` is only returned from DSPy's predictions
    order = min([dp.get("order", 1) for dp in edges_data] + already_order)
    # 计算总权重
    weight = sum([dp["weight"] for dp in edges_data] + already_weights)
    # 合并并去重描述，排序后转为字符串
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in edges_data] + already_description))
    )
    # 合并并去重源ID
    source_id = GRAPH_FIELD_SEP.join(
        set([dp["source_id"] for dp in edges_data] + already_source_ids)
    )
    # 确保src_id和tgt_id在图中存在节点，如果不存在则插入
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
    description = await _handle_entity_relation_summary(
        (src_id, tgt_id), description
    )
    # 插入/更新src_id和tgt_id之间的边
    await knwoledge_graph_inst.upsert_edge(
        src_id,
        tgt_id,
        edge_data=dict(
            weight=weight, description=description, source_id=source_id, order=order
        ),
    )
