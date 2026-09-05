"""
Shared utility functions — pure helpers with no side effects.
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
# Logging
# ============================================================================

logger = logging.getLogger("multimodal-graphrag")
_ENCODER = None


# ============================================================================
# Embedding wrapper
# ============================================================================

@dataclass
class EmbeddingFunc:
    embedding_dim: int
    max_token_size: int
    func: callable

    async def __call__(self, *args, **kwargs) -> np.ndarray:
        return await self.func(*args, **kwargs)


def wrap_embedding_func_with_attrs(**kwargs):
    def decorator(func) -> EmbeddingFunc:
        return EmbeddingFunc(**kwargs, func=func)
    return decorator


# ============================================================================
# Text helpers
# ============================================================================

def clean_str(input: Any) -> str:
    if not isinstance(input, str):
        return input
    result = html.unescape(input.strip())
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", result)


def split_string_by_multi_markers(content: str, markers: list[str]) -> list[str]:
    if not markers:
        return [content]
    pattern = "|".join(re.escape(m) for m in markers)
    return [r.strip() for r in re.split(pattern, content) if r.strip()]


def is_float_regex(value: str) -> bool:
    return bool(re.match(r"^[-+]?[0-9]*\.?[0-9]+$", value))


def list_of_list_to_csv(data: list[list[str]]) -> str:
    return "\n".join(
        [
            ",".join([f'"{ii!s}"' if "," in str(ii) else str(ii) for ii in i])
            for i in data
        ]
    )


def truncate_list_by_token_size(list_data: list, key: callable, max_token_size: int) -> list:
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
# Tiktoken
# ============================================================================

def _get_encoder(model_name: str = "gpt-4o"):
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = tiktoken.encoding_for_model(model_name)
    return _ENCODER


def encode_string_by_tiktoken(content: str, model_name: str = "gpt-4o") -> list[int]:
    return _get_encoder(model_name).encode(content)


def decode_tokens_by_tiktoken(tokens: list[int], model_name: str = "gpt-4o") -> str:
    return _get_encoder(model_name).decode(tokens)


# ============================================================================
# Hashing
# ============================================================================

def compute_args_hash(*args) -> str:
    return md5(str(args).encode()).hexdigest()


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    return prefix + md5(content.encode()).hexdigest()


# ============================================================================
# Message formatting
# ============================================================================

def pack_user_ass_to_openai_messages(*args: str) -> list[dict]:
    roles = ["user", "assistant"]
    return [{"role": roles[i % 2], "content": c} for i, c in enumerate(args)]


# ============================================================================
# Async concurrency limiter
# ============================================================================

def limit_async_func_call(max_size: int, wait_time: float = 0.0001):
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
# File I/O
# ============================================================================

def write_json(data: Any, file_path: str):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: str) -> Any:
    if not os.path.exists(file_path):
        return None
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def check_json_not_empty(file_path: str) -> bool:
    data = load_json(file_path)
    return bool(data)


def ensure_quoted(text: str) -> str:
    if not (text.startswith('"') and text.endswith('"')):
        return f'"{text}"'
    return text


# ============================================================================
# Graph file helpers
# ============================================================================

def get_latest_graphml_file(folder_path: str) -> tuple[str, str]:
    pattern = r"graph_merged_image_(\d+)\.graphml"
    max_num = -1
    namespace = "chunk_entity_relation"
    file_path = None

    if not os.path.isdir(folder_path):
        return namespace, os.path.join(folder_path, "graph_chunk_entity_relation.graphml")

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
