"""
图像知识图谱构建模块

从图像中提取实体和关系，构建知识图谱。

主要功能:
1. 图像分割 (YOLO) - 提取图像特征块
2. 特征块实体提取 - 为每个特征块生成描述
3. 实体关系构建 - 建立实体之间的关系
"""
import asyncio
import base64
import os
import shutil
import re
from functools import partial
from pathlib import Path
from typing import cast, Type, Union
from dataclasses import dataclass
from collections import defaultdict

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm
from ultralytics import YOLO

from ..core.base import load_json, limit_async_func_call, logger, split_string_by_multi_markers
from .utils import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction,
    _merge_nodes_then_upsert,
    _merge_edges_then_upsert,
)
from ..llm import multimodel_if_cache
from ..core.prompt import PROMPTS
from ..core.storage import BaseGraphStorage, BaseKVStorage, JsonKVStorage, NetworkXStorage, StorageNameSpace
from .. import parameter


# ============================================================================
# 常量
# ============================================================================

TUPLE_DELIMITER = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
RECORD_DELIMITER = PROMPTS["DEFAULT_RECORD_DELIMITER"]
COMPLETION_DELIMITER = PROMPTS["DEFAULT_COMPLETION_DELIMITER"]
MIN_IMAGE_SIZE = 28  # 最小图像尺寸


# ============================================================================
# 图像分割
# ============================================================================

async def extract_feature_chunks(image_path: str) -> str:
    """
    使用YOLO对图像进行分割，提取特征块。
    
    Returns:
        特征块保存目录路径
    """
    image_name = Path(image_path).stem
    save_dir = os.path.join(parameter.WORKING_DIR, "images", image_name)
    os.makedirs(save_dir, exist_ok=True)
    
    # 检查是否需要分割
    image_data = load_json(os.path.join(parameter.WORKING_DIR, "kv_store_image_data.json")) or {}
    should_segment = any(
        v.get("image_path") == image_path and v.get("segmentation", False)
        for v in image_data.values()
    )
    
    if not should_segment:
        return save_dir
    
    # YOLO分割
    yolo_path = os.path.join(os.path.dirname(__file__), "yolov8n-seg.pt")
    model = YOLO(yolo_path)
    results = model(image_path, device='cpu')
    
    for result in results:
        img = np.copy(result.orig_img)
        img_name = Path(result.path).stem
        
        for idx, detection in enumerate(result):
            label = detection.names[detection.boxes.cls.tolist().pop()]
            
            # 创建掩膜
            mask = np.zeros(img.shape[:2], np.uint8)
            contour = detection.masks.xy.pop().astype(np.int32).reshape(-1, 1, 2)
            cv2.drawContours(mask, [contour], -1, (255, 255, 255), cv2.FILLED)
            
            # 应用掩膜
            mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            isolated = cv2.bitwise_and(mask_3ch, img)
            
            # 裁剪到边界框
            x1, y1, x2, y2 = detection.boxes.xyxy[0].cpu().numpy().astype(np.int32)
            cropped = isolated[y1:y2, x1:x2]
            
            # 保存
            save_path = os.path.join(save_dir, f"{img_name}_{label}-{idx}.jpg")
            cv2.imwrite(save_path, cropped)
    
    return save_dir


# ============================================================================
# 实体提取辅助函数
# ============================================================================

def _encode_image_base64(image_path: str) -> str:
    """将图像编码为Base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_jpg_files(directory: str) -> list[str]:
    """获取目录下所有JPG文件路径"""
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith('.jpg')
    ]


def _build_entity_string(name: str, entity_type: str, description: str) -> str:
    """构建实体字符串"""
    return f'("entity"{TUPLE_DELIMITER}"{name}"{TUPLE_DELIMITER}"{entity_type}"{TUPLE_DELIMITER}"{description}"){RECORD_DELIMITER}'


def _build_relationship_string(src: str, tgt: str, description: str, weight: int = 10) -> str:
    """构建关系字符串"""
    return f'("relationship"{TUPLE_DELIMITER}"{src}"{TUPLE_DELIMITER}"{tgt}"{TUPLE_DELIMITER}"{description}"{TUPLE_DELIMITER}{weight}){RECORD_DELIMITER}'


# ============================================================================
# 特征块实体构建
# ============================================================================

async def feature_image_entity_construction(feature_dir: str, llm_func) -> list[str]:
    """为特征块图像生成实体描述"""
    entities = []
    jpg_files = _get_jpg_files(feature_dir)
    
    if not jpg_files:
        return entities
    
    prompt_user = PROMPTS["feature_image_description_user"]
    prompt_system = PROMPTS["feature_image_description_system"]
    
    for image_path in jpg_files:
        filename = os.path.basename(image_path)
        
        # 检查图像尺寸
        with Image.open(image_path) as img:
            width, height = img.size
        
        if width <= MIN_IMAGE_SIZE or height <= MIN_IMAGE_SIZE:
            logger.info(f"🖼️ 跳过小图像: {filename} ({width}x{height})")
            os.remove(image_path)
            continue
        
        img_base64 = _encode_image_base64(image_path)
        description = await llm_func(
            user_prompt=prompt_user,
            img_base=img_base64,
            system_prompt=prompt_system
        )
        
        entity = _build_entity_string(filename, "img", description)
        entities.append(entity.replace("\n", ""))
    
    return entities


async def feature_image_relationship_construction(
    feature_dir: str, 
    entity_descriptions: str, 
    llm_func
) -> list[str]:
    """构建特征块与实体之间的关系"""
    relationships = []
    jpg_files = _get_jpg_files(feature_dir)
    
    if not jpg_files:
        return relationships
    
    prompt_system = PROMPTS["entity_alignment_system"].format(
        tuple_delimiter=TUPLE_DELIMITER,
        record_delimiter=RECORD_DELIMITER
    )
    
    for image_path in jpg_files:
        filename = os.path.basename(image_path)
        prompt_user = PROMPTS["entity_alignment_user"].format(
            entity_description=entity_descriptions,
            feature_image_name=filename
        )
        
        img_base64 = _encode_image_base64(image_path)
        result = await llm_func(
            user_prompt=prompt_user,
            img_base=img_base64,
            system_prompt=prompt_system
        )
        relationships.append(result)
    
    return relationships


async def extract_entities_from_image(image_path: str, llm_func) -> str:
    """从图像中提取实体"""
    prompt = PROMPTS["image_entity_extraction"].format(
        tuple_delimiter=TUPLE_DELIMITER,
        record_delimiter=RECORD_DELIMITER,
        completion_delimiter=COMPLETION_DELIMITER,
        entity_types=",".join(PROMPTS["DEFAULT_ENTITY_TYPES"]),
    )
    
    img_base64 = _encode_image_base64(image_path)
    return await llm_func(
        user_prompt="Please output the results in the format provided in the example.\nOutput:",
        img_base=img_base64,
        system_prompt=prompt
    )


async def build_original_image_entity(
    image_path: str, 
    feature_entities: list[str], 
    extracted_result: str
) -> list[str]:
    """构建原始图像的实体和关系"""
    results = []
    
    image_data = load_json(os.path.join(parameter.WORKING_DIR, "kv_store_image_data.json")) or {}
    
    # 查找当前图像信息
    filename = None
    description = ""
    for key, info in image_data.items():
        if info.get("image_path") == image_path:
            filename = key
            description = info.get("description", "")
            break
    
    if not filename:
        return results
    
    # 添加原始图像实体
    entity = _build_entity_string(filename, "ori_img", description)
    results.append(entity.replace("\n", ""))
    
    # 添加特征块与原始图像的关系
    pattern = r'\"([^\"]+?\.jpg)\"'
    for feature_entity in feature_entities:
        matches = re.findall(pattern, feature_entity)
        if matches:
            rel = _build_relationship_string(
                matches[0], filename, f"{matches[0]}是{filename}的图像特征块。"
            )
            results.append(rel)
    
    # 添加提取实体与原始图像的关系
    entity_pattern = r'\"entity\"\<\|\>\"([^\"]+?)\"'
    for entity_name in re.findall(entity_pattern, extracted_result):
        rel = _build_relationship_string(
            entity_name, filename, f"{entity_name}是从{filename}中提取的实体。"
        )
        results.append(rel)
    
    return results


def format_entities_result(result: str) -> str:
    """格式化实体提取结果"""
    pattern = r'\("entity"<\|>"([^"]+)"<\|>"[^"]*"<\|>"([^"]+)"\)'
    entities = re.findall(pattern, result)
    return "\n".join([f'"{e}"-"{d}"' for e, d in entities])


# ============================================================================
# 主提取函数
# ============================================================================

async def extract_entities(
    cache_storage: BaseKVStorage,
    image_path: str,
    feature_dir: str,
    knwoledge_graph_inst: BaseGraphStorage,
) -> Union[BaseGraphStorage, None]:
    """从图像提取实体并构建知识图谱"""
    
    llm_func = limit_async_func_call(16)(
        partial(multimodel_if_cache, hashing_kv=cache_storage)
    )
    
    # 提取各类实体和关系
    feature_entities = await feature_image_entity_construction(feature_dir, llm_func)
    image_entities = await extract_entities_from_image(image_path, llm_func)
    formatted_entities = format_entities_result(image_entities)
    relationships = await feature_image_relationship_construction(feature_dir, formatted_entities, llm_func)
    original_entities = await build_original_image_entity(image_path, feature_entities, image_entities)
    
    # 合并所有结果
    all_results = feature_entities + relationships + original_entities
    final_result = "\n" + "\n".join(all_results) + image_entities.strip()
    
    # 解析记录
    records = split_string_by_multi_markers(
        final_result, [RECORD_DELIMITER, COMPLETION_DELIMITER]
    )
    
    maybe_nodes = defaultdict(list)
    maybe_edges = defaultdict(list)
    
    for record in records:
        match = re.search(r"\((.*)\)", record)
        if not match:
            continue
        
        attrs = split_string_by_multi_markers(match.group(1), [TUPLE_DELIMITER])
        
        entity = await _handle_single_entity_extraction(attrs, image_path)
        if entity:
            maybe_nodes[entity["entity_name"]].append(entity)
            continue
        
        relation = await _handle_single_relationship_extraction(attrs, image_path)
        if relation:
            maybe_edges[(relation["src_id"], relation["tgt_id"])].append(relation)
    
    # 合并节点（按名称去重）
    merged_nodes = {}
    for name, data_list in maybe_nodes.items():
        merged_nodes[name] = data_list
    
    # 合并边（无向图排序）
    merged_edges = {}
    for key, data_list in maybe_edges.items():
        sorted_key = tuple(sorted(key))
        merged_edges.setdefault(sorted_key, []).extend(data_list)
    
    # 更新知识图谱
    all_entities = await asyncio.gather(*[
        _merge_nodes_then_upsert(k, v, knwoledge_graph_inst)
        for k, v in merged_nodes.items()
    ])
    
    await asyncio.gather(*[
        _merge_edges_then_upsert(k[0], k[1], v, knwoledge_graph_inst)
        for k, v in merged_edges.items()
    ])
    
    if not all_entities:
        logger.warning("未提取到任何实体")
        return None
    
    return knwoledge_graph_inst


# ============================================================================
# 提取器类
# ============================================================================

@dataclass
class ImageEntityExtractor:
    """图像实体提取器"""
    extraction_func: callable = extract_entities
    kv_storage_cls: Type[BaseKVStorage] = JsonKVStorage
    graph_storage_cls: Type[BaseGraphStorage] = NetworkXStorage
    
    def __post_init__(self):
        self.llm_cache = self.kv_storage_cls(
            namespace="multimodel_llm_response_cache",
            storage_dir=parameter.CACHE_PATH
        )
        self.graph = self.graph_storage_cls(namespace="image_entity_relation")
    
    async def extract(self, image_path: str):
        """提取单张图像的实体"""
        try:
            feature_dir = await extract_feature_chunks(image_path)
            logger.info("🔍 正在提取实体...")
            
            result = await self.extraction_func(
                self.llm_cache,
                image_path,
                feature_dir,
                knwoledge_graph_inst=self.graph,
            )
            
            if result is None:
                logger.warning("未找到实体")
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

# ============================================================================
# 入口函数
# ============================================================================

async def img2graph(images_dir: str):
    """
    处理目录下所有图像，构建知识图谱。
    
    Args:
        images_dir: 包含JPG图像的目录路径
    """
    jpg_files = _get_jpg_files(images_dir)
    
    if not jpg_files:
        return
    
    for image_path in tqdm(jpg_files, desc="🖼️ 图像实体提取", unit="张"):
        image_name = Path(image_path).stem
        target_graph_path = os.path.join(
            parameter.WORKING_DIR, "images", image_name,
            f"graph_{image_name}_entity_relation.graphml"
        )
        
        if os.path.exists(target_graph_path):
            # logger.info(f"✓ 跳过已处理图像: {image_name}")
            continue

        extractor = ImageEntityExtractor()
        await extractor.extract(image_path)
        
        # 移动生成的图谱文件
        src = os.path.join(parameter.WORKING_DIR, "graph_image_entity_relation.graphml")
        dst = target_graph_path
        
        if os.path.exists(src):
            shutil.move(src, dst)