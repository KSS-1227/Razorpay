"""
LLM 交互模块

提供与大语言模型 (LLM) 和多模态模型 (MM-LLM) 的交互接口，包括同步和异步方法，
以及基于 KV 存储的缓存机制。
"""
import ast
import json
import re
from typing import Any, List, Optional, Union

import numpy as np
from openai import AsyncOpenAI, OpenAI

from ..core.base import compute_args_hash, logger, wrap_embedding_func_with_attrs
from ..parameter import (
    API_BASE,
    API_KEY,
    EMBED_MODEL,
    MM_API_BASE,
    MM_API_KEY,
    MM_MODEL_NAME,
    MODEL_NAME,
)
from ..core.storage import BaseKVStorage

# ============================================================================
# 全局客户端缓存
# ============================================================================

_CLIENTS = {
    "text_sync": None,
    "text_async": None,
    "mm_sync": None,
    "mm_async": None,
}


def _get_client(is_async: bool = False, is_multimodal: bool = False):
    """获取 OpenAI 客户端实例 (单例模式)"""
    key = f"{'mm' if is_multimodal else 'text'}_{'async' if is_async else 'sync'}"
    
    if _CLIENTS[key] is None:
        api_key = MM_API_KEY if is_multimodal else API_KEY
        base_url = MM_API_BASE if is_multimodal else API_BASE
        client_cls = AsyncOpenAI if is_async else OpenAI
        _CLIENTS[key] = client_cls(api_key=api_key, base_url=base_url)
    
    return _CLIENTS[key]


# ============================================================================
# 嵌入函数
# ============================================================================

@wrap_embedding_func_with_attrs(
    embedding_dim=EMBED_MODEL.get_sentence_embedding_dimension(),
    max_token_size=EMBED_MODEL.max_seq_length,
)
async def local_embedding(texts: list[str]) -> np.ndarray:
    """本地嵌入函数"""
    return EMBED_MODEL.encode(texts)


# ============================================================================
# 文本 LLM 接口
# ============================================================================

async def model_if_cache(
    prompt: str,
    system_prompt: str = None,
    history_messages: List[dict] = [],
    **kwargs
) -> str:
    """
    异步调用文本 LLM，支持缓存。
    
    Args:
        hashing_kv: 缓存存储对象 (从kwargs中获取)
    """
    client = _get_client(is_async=True, is_multimodal=False)
    hashing_kv: Optional[BaseKVStorage] = kwargs.pop("hashing_kv", None)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    # 缓存检查
    args_hash = None
    if hashing_kv:
        args_hash = compute_args_hash(MODEL_NAME, messages)
        cached = await hashing_kv.get_by_id(args_hash)
        if cached:
            return cached["return"]

    # 调用 API
    response = await client.chat.completions.create(
        model=MODEL_NAME, messages=messages, **kwargs
    )
    content = response.choices[0].message.content

    # 写入缓存
    if hashing_kv and args_hash:
        await hashing_kv.upsert(
            {args_hash: {"return": content, "model": MODEL_NAME}}
        )
        await hashing_kv.index_done_callback()
        
    return content


def get_llm_response(cur_prompt: str, system_content: str) -> str:
    """同步调用文本 LLM"""
    client = _get_client(is_async=False, is_multimodal=False)
    
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": cur_prompt},
        ],
        max_tokens=4096,
        frequency_penalty=0.3,
    )
    return completion.choices[0].message.content


# ============================================================================
# 多模态 LLM 接口
# ============================================================================

async def multimodel_if_cache(
    user_prompt: str,
    img_base: str,
    system_prompt: str,
    history_messages: List[dict] = [],
    **kwargs
) -> str:
    """
    异步调用多模态 LLM，支持缓存。
    """
    client = _get_client(is_async=True, is_multimodal=True)
    hashing_kv: Optional[BaseKVStorage] = kwargs.pop("hashing_kv", None)
    
    messages = []
    messages.extend(history_messages)
    messages.append({
        "role": "system",
        "content": [{"type": "text", "text": system_prompt}]
    })
    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base}"}},
            {"type": "text", "text": user_prompt}
        ]
    })

    # 缓存检查
    args_hash = None
    if hashing_kv:
        args_hash = compute_args_hash(MM_MODEL_NAME, messages)
        cached = await hashing_kv.get_by_id(args_hash)
        if cached:
            return cached["return"]

    # 调用 API
    response = await client.chat.completions.create(
        model=MM_MODEL_NAME, messages=messages, **kwargs
    )
    content = response.choices[0].message.content

    # 写入缓存
    if hashing_kv and args_hash:
        await hashing_kv.upsert(
            {args_hash: {"return": content, "model": MM_MODEL_NAME}}
        )
        await hashing_kv.index_done_callback()

    return content


def get_mmllm_response(cur_prompt: str, system_content: str, img_base: str) -> str:
    """同步调用多模态 LLM"""
    client = _get_client(is_async=False, is_multimodal=True)
    
    completion = client.chat.completions.create(
        model=MM_MODEL_NAME,
        messages=[
            {"role": "system", "content": [{"type": "text", "text": system_content}]},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base}"}},
                {"type": "text", "text": cur_prompt}
            ]},
        ],
        max_tokens=4096,
    )
    return completion.choices[0].message.content


# ============================================================================
# JSON 处理工具
# ============================================================================

def normalize_to_json(output: str) -> Optional[dict]:
    """从输出中提取并解析 JSON 对象"""
    output = output.strip()
    
    # 1. 尝试提取 Markdown 代码块
    match = re.search(r"```(?:json)?\s*(.*?)```", output, re.DOTALL)
    if match:
        output = match.group(1)
        
    # 2. 寻找最外层的 {}
    match = re.search(r"\{.*\}", output, re.DOTALL)
    if match:
        json_str = match.group(0)
    else:
        logger.debug(f"未找到 JSON 对象: {output[:100]}...")
        return None

    # 3. 尝试标准 JSON 解析
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 4. 尝试修复常见格式错误 (Python bools -> JSON bools)
    try:
        repaired_str = re.sub(r"\bTrue\b", "true", json_str)
        repaired_str = re.sub(r"\bFalse\b", "false", json_str)
        return json.loads(repaired_str)
    except json.JSONDecodeError:
        pass
        
    # 5. Fallback: 使用 ast 解析 Python 字典 (处理单引号、True/False)
    try:
        return ast.literal_eval(json_str)
    except (ValueError, SyntaxError) as e:
        logger.debug(f"JSON解码失败: {e}")
        return None


def normalize_to_json_list(output: str) -> List[Any]:
    """从输出中提取并解析 JSON 列表，支持容错解析"""
    cleaned = output.replace('\\"', '"').strip()
    match = re.search(r"\[\s*(\{.*?\})*?\s*]", cleaned, re.DOTALL)
    
    if not match:
        logger.warning("未找到有效的JSON列表片段")
        return []
        
    json_str = match.group(0)
    # 修复常见格式错误
    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = re.sub(r",\s*}$", "}", json_str)

    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        logger.warning("完整列表解析失败，尝试逐项解析...")
    
    # 逐项解析回退方案
    items = []
    for item_match in re.finditer(r"\{.*?\}", json_str, re.DOTALL):
        try:
            items.append(json.loads(item_match.group(0)))
        except json.JSONDecodeError:
            continue
            
    return items
