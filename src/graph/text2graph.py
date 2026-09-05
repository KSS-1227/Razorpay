"""
文本知识图谱构建模块

从文本块中提取实体和关系，构建知识图谱。

主要功能:
1. 遍历文本块
2. 使用LLM提取实体和关系
3. 合并重复实体
4. 更新知识图谱
"""
import asyncio
import json
import os
import re
from collections import defaultdict
from functools import partial
from typing import Union, cast, Type
from dataclasses import dataclass

from tqdm import tqdm

from ..core.base import (
    logger,
    pack_user_ass_to_openai_messages,
    split_string_by_multi_markers,
    limit_async_func_call,
)
from .utils import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction,
    _merge_nodes_then_upsert,
    _merge_edges_then_upsert,
)
from ..llm import model_if_cache
from ..core.prompt import PROMPTS
from ..core.storage import (
    BaseGraphStorage,
    BaseKVStorage,
    JsonKVStorage,
    NetworkXStorage,
    StorageNameSpace,
    TextChunkSchema,
)
from .. import parameter


# ============================================================================
# 常量
# ============================================================================

TUPLE_DELIMITER = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
RECORD_DELIMITER = PROMPTS["DEFAULT_RECORD_DELIMITER"]
COMPLETION_DELIMITER = PROMPTS["DEFAULT_COMPLETION_DELIMITER"]
PROCESS_TICKERS = PROMPTS["process_tickers"]


# ============================================================================
# 主提取函数
# ============================================================================

async def extract_entities(
    cache_storage: BaseKVStorage,
    chunks: dict[str, TextChunkSchema],
    knwoledge_graph_inst: BaseGraphStorage,
) -> Union[BaseGraphStorage, None]:
    """
    从文本块中提取实体和关系。
    
    Args:
        cache_storage: 缓存存储
        chunks: 文本块字典
        knwoledge_graph_inst: 知识图谱实例
    
    Returns:
        更新后的知识图谱，如果未提取到实体则返回None
    """
    output_path = os.path.join(parameter.WORKING_DIR, "kv_store_chunk_knowledge_graph.json")
    
    llm_func = limit_async_func_call(16)(
        partial(model_if_cache, hashing_kv=cache_storage)
    )
    
    max_gleaning = parameter.ENTITY_EXTRACT_MAX_GLEANING
    ordered_chunks = list(chunks.items())
    
    # 提示模板
    entity_prompt = PROMPTS["entity_extraction"]
    continue_prompt = PROMPTS["entity_continue_extraction"]
    loop_prompt = PROMPTS["entity_if_loop_extraction"]
    
    context = {
        "tuple_delimiter": TUPLE_DELIMITER,
        "record_delimiter": RECORD_DELIMITER,
        "completion_delimiter": COMPLETION_DELIMITER,
        "entity_types": ",".join(PROMPTS["DEFAULT_ENTITY_TYPES"]),
    }
    
    # 统计计数
    stats = {"processed": 0, "entities": 0, "relations": 0}
    chunk_kg_info = {}
    
    async def process_chunk(chunk_item: tuple[str, TextChunkSchema]) -> tuple[dict, dict]:
        """处理单个文本块"""
        chunk_key, chunk_data = chunk_item
        content = chunk_data["content"]
        chunk_index = chunk_data["chunk_order_index"]
        
        # 第一次提取
        prompt = entity_prompt.format(**context, input_text=content)
        result = await llm_func(prompt)
        history = pack_user_ass_to_openai_messages(prompt, result)
        
        # 迭代提取
        for i in range(max_gleaning):
            glean_result = await llm_func(continue_prompt, history_messages=history)
            history += pack_user_ass_to_openai_messages(continue_prompt, glean_result)
            result += glean_result
            
            if i < max_gleaning - 1:
                should_continue = await llm_func(loop_prompt, history_messages=history)
                if should_continue.strip().strip("'\"").lower() != "yes":
                    break
        
        # 解析记录
        records = split_string_by_multi_markers(result, [RECORD_DELIMITER, COMPLETION_DELIMITER])
        
        nodes = defaultdict(list)
        edges = defaultdict(list)
        chunk_result = {"chunk_key": chunk_key, "entities": [], "relationships": []}
        
        for record in records:
            match = re.search(r"\((.*)\)", record)
            if not match:
                continue
            
            attrs = split_string_by_multi_markers(match.group(1), [TUPLE_DELIMITER])
            
            entity = await _handle_single_entity_extraction(attrs, chunk_key)
            if entity:
                nodes[entity["entity_name"]].append(entity)
                chunk_result["entities"].append(entity)
                continue
            
            relation = await _handle_single_relationship_extraction(attrs, chunk_key)
            if relation:
                edges[(relation["src_id"], relation["tgt_id"])].append(relation)
                chunk_result["relationships"].append(relation)
        
        chunk_kg_info[chunk_index] = chunk_result
        return dict(nodes), dict(edges)
    
    # 并发处理所有文本块（带进度条）
    tasks = [process_chunk(c) for c in ordered_chunks]
    results = []
    for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="📝 文本实体提取", unit="块"):
        result = await coro
        results.append(result)
    
    # 保存块级知识图谱信息
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunk_kg_info, f, ensure_ascii=False, indent=2)
    
    # 汇总所有节点和边
    all_nodes = defaultdict(list)
    all_edges = defaultdict(list)
    
    for nodes, edges in results:
        for k, v in nodes.items():
            all_nodes[k].extend(v)
        for k, v in edges.items():
            all_edges[tuple(sorted(k))].extend(v)  # 无向图排序
    
    # 更新知识图谱
    entities_data = await asyncio.gather(*[
        _merge_nodes_then_upsert(k, v, knwoledge_graph_inst)
        for k, v in all_nodes.items()
    ])
    
    await asyncio.gather(*[
        _merge_edges_then_upsert(k[0], k[1], v, knwoledge_graph_inst)
        for k, v in all_edges.items()
    ])
    
    if not entities_data:
        logger.warning("未提取到任何实体")
        return None
    
    return knwoledge_graph_inst


# ============================================================================
# 提取器类
# ============================================================================

@dataclass
class TextEntityExtractor:
    """文本实体提取器"""
    extraction_func: callable = extract_entities
    kv_storage_cls: Type[BaseKVStorage] = JsonKVStorage
    graph_storage_cls: Type[BaseGraphStorage] = NetworkXStorage
    
    def __post_init__(self):
        self.llm_cache = self.kv_storage_cls(
            namespace="llm_response_cache",
            storage_dir=parameter.CACHE_PATH
        )
        self.graph = self.graph_storage_cls(namespace="chunk_entity_relation")
    
    async def text_entity_extraction(self, chunks: dict):
        """提取文本实体"""
        try:
            logger.info("🔍 正在提取实体...")
            
            result = await self.extraction_func(
                self.llm_cache,
                chunks,
                knwoledge_graph_inst=self.graph,
            )
            
            if result is None:
                logger.warning("未找到新实体")
            else:
                self.graph = result
        finally:
            await self._save()
    
    async def _save(self):
        """保存存储"""
        tasks = [
            cast(StorageNameSpace, s).index_done_callback()
            for s in [self.llm_cache, self.graph] if s
        ]
        await asyncio.gather(*tasks)