"""
基础工具模块 - 提供项目通用的工具函数和类

包含:
- 文本处理: clean_str, split_string_by_multi_markers
- Token处理: encode_string_by_tiktoken, decode_tokens_by_tiktoken
- 哈希计算: compute_args_hash, compute_mdhash_id
- 异步控制: limit_async_func_call
- 文件操作: load_json, write_json
- 嵌入函数: EmbeddingFunc, wrap_embedding_func_with_attrs
"""
import asyncio
import html
import json
import logging
import os
import re
from dataclasses import dataclass
from functools import wraps
from hashlib import md5
from typing import Any

import numpy as np
import tiktoken

# ============================================================================
# 全局配置
# ============================================================================

logger = logging.getLogger("multimodal-graphrag")
_ENCODER = None  # tiktoken编码器缓存


# ============================================================================
# 嵌入函数
# ============================================================================

@dataclass
class EmbeddingFunc:
    """嵌入函数包装类"""
    embedding_dim: int
    max_token_size: int
    func: callable

    async def __call__(self, *args, **kwargs) -> np.ndarray:
        return await self.func(*args, **kwargs)


def wrap_embedding_func_with_attrs(**kwargs):
    """将函数包装为EmbeddingFunc对象的装饰器"""
    def decorator(func) -> EmbeddingFunc:
        return EmbeddingFunc(**kwargs, func=func)
    return decorator


# ============================================================================
# 文本处理
# ============================================================================

def clean_str(input: Any) -> str:
    """清理字符串：移除HTML转义和控制字符"""
    if not isinstance(input, str):
        return input
    result = html.unescape(input.strip())
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", result)


def split_string_by_multi_markers(content: str, markers: list[str]) -> list[str]:
    """按多个分隔符拆分字符串"""
    if not markers:
        return [content]
    pattern = "|".join(re.escape(m) for m in markers)
    return [r.strip() for r in re.split(pattern, content) if r.strip()]


def is_float_regex(value: str) -> bool:
    """判断字符串是否为浮点数"""
    return bool(re.match(r"^[-+]?[0-9]*\.?[0-9]+$", value))


def list_of_list_to_csv(data: list[list[str]]) -> str:
    """将二维列表转换为CSV格式字符串"""
    return "\n".join(
        [
            ",".join([f'"{str(ii)}"' if "," in str(ii) else str(ii) for ii in i])
            for i in data
        ]
    )


def truncate_list_by_token_size(list_data: list, key: callable, max_token_size: int) -> list:
    """根据token大小截断列表"""
    if max_token_size <= 0:
        return []
        
    result = []
    current_token_size = 0
    
    for item in list_data:
        content = key(item)
        token_size = len(encode_string_by_tiktoken(content))
        
        if current_token_size + token_size > max_token_size:
            break
            
        result.append(item)
        current_token_size += token_size
        
    return result


# ============================================================================
# Token处理 (tiktoken)
# ============================================================================

def _get_encoder(model_name: str = "gpt-4o"):
    """获取或创建tiktoken编码器（单例）"""
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = tiktoken.encoding_for_model(model_name)
    return _ENCODER


def encode_string_by_tiktoken(content: str, model_name: str = "gpt-4o") -> list[int]:
    """将字符串编码为token列表"""
    return _get_encoder(model_name).encode(content)


def decode_tokens_by_tiktoken(tokens: list[int], model_name: str = "gpt-4o") -> str:
    """将token列表解码为字符串"""
    return _get_encoder(model_name).decode(tokens)


# ============================================================================
# 哈希计算
# ============================================================================

def compute_args_hash(*args) -> str:
    """计算参数的MD5哈希值"""
    return md5(str(args).encode()).hexdigest()


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    """计算内容的MD5哈希ID，可添加前缀"""
    return prefix + md5(content.encode()).hexdigest()


# ============================================================================
# 消息格式化
# ============================================================================

def pack_user_ass_to_openai_messages(*args: str) -> list[dict]:
    """将对话内容打包为OpenAI消息格式（user/assistant交替）"""
    roles = ["user", "assistant"]
    return [{"role": roles[i % 2], "content": c} for i, c in enumerate(args)]


# ============================================================================
# 异步控制
# ============================================================================

def limit_async_func_call(max_size: int, wait_time: float = 0.0001):
    """
    异步函数并发限制装饰器。
    
    Args:
        max_size: 最大并发数
        wait_time: 等待轮询间隔（秒）
    """
    def decorator(func):
        _current = 0

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal _current
            while _current >= max_size:
                await asyncio.sleep(wait_time)
            _current += 1
            try:
                return await func(*args, **kwargs)
            finally:
                _current -= 1

        return wrapper
    return decorator


# ============================================================================
# 文件操作
# ============================================================================

def write_json(data: Any, file_path: str):
    """将数据写入JSON文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: str) -> Any:
    """从JSON文件加载数据，文件不存在返回None"""
    if not os.path.exists(file_path):
        return None
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def check_json_not_empty(file_path: str) -> bool:
    """检查JSON文件是否存在且内容非空"""
    data = load_json(file_path)
    return bool(data)


def ensure_quoted(text: str) -> str:
    """确保字符串两端有双引号"""
    if not (text.startswith('"') and text.endswith('"')):
        return f'"{text}"'
    return text


# ============================================================================
# 图文件工具
# ============================================================================

def get_latest_graphml_file(folder_path: str) -> tuple[str, str]:
    """
    获取目录中最新的合并图文件。
    
    返回: (namespace, file_path)
    """
    pattern = r"graph_merged_image_(\d+)\.graphml"
    max_num = -1
    namespace = "chunk_entity_relation"
    file_path = None

    for filename in os.listdir(folder_path):
        match = re.match(pattern, filename)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
                namespace = f"merged_image_{num}"
                file_path = os.path.join(folder_path, filename)

    if file_path is None:
        file_path = os.path.join(folder_path, "graph_chunk_entity_relation.graphml")
    
    return namespace, file_path