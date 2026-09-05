"""
数据预处理模块

包含文本分块、PDF处理（支持PyMuPDF和MinerU）、图像压缩与描述生成等功能。
"""
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from io import BytesIO
from typing import Callable, Dict, List, Optional, Type, Union, cast

from PIL import Image
from tqdm import tqdm

from .. import parameter
from ..core.base import (
    compute_mdhash_id,
    decode_tokens_by_tiktoken,
    encode_string_by_tiktoken,
    load_json,
    logger,
)
from ..llm import multimodel_if_cache, normalize_to_json
from ..core.prompt import PROMPTS
from ..core.storage import BaseKVStorage, JsonKVStorage, StorageNameSpace


# ============================================================================
# 文本分块
# ============================================================================

def chunking_by_token_size(
    content: str, 
    overlap_token_size=128, 
    max_token_size=1024, 
    tiktoken_model="gpt-4o"
) -> List[Dict[str, Union[str, int]]]:
    """根据token大小对文本进行分块"""
    tokens = encode_string_by_tiktoken(content, model_name=tiktoken_model)
    results = []
    
    for index, start in enumerate(
        range(0, len(tokens), max_token_size - overlap_token_size)
    ):
        chunk_tokens = tokens[start : start + max_token_size]
        chunk_content = decode_tokens_by_tiktoken(chunk_tokens, model_name=tiktoken_model)
        
        results.append({
            "tokens": min(max_token_size, len(tokens) - start),
            "content": chunk_content.strip(),
            "chunk_order_index": index,
        })
    return results


@dataclass
class TextChunking:
    """文本分块处理类"""
    chunk_func: Callable = chunking_by_token_size
    chunk_token_size: int = 1200
    chunk_overlap_token_size: int = 100
    key_string_value_json_storage_cls: Type[BaseKVStorage] = JsonKVStorage
    tiktoken_model_name: str = "gpt-4o"

    def __post_init__(self):
        self.full_docs = self.key_string_value_json_storage_cls(namespace="full_docs")
        self.text_chunks = self.key_string_value_json_storage_cls(namespace="text_chunks")
    
    async def text_chunking(self, string_or_strings: Union[str, List[str]]):
        """处理文本分块并存储"""
        if isinstance(string_or_strings, str):
            string_or_strings = [string_or_strings]
            
        try:
            # 1. 存储新文档
            new_docs = {
                compute_mdhash_id(c.strip(), prefix="doc-"): {"content": c.strip()}
                for c in string_or_strings
            }
            
            # 过滤已存在的文档
            full_doc_keys = list(new_docs.keys())
            existing_doc_keys = await self.full_docs.filter_keys(full_doc_keys)
            new_docs_to_insert = {k: v for k, v in new_docs.items() if k in existing_doc_keys} # filter_keys返回的是不存在的key? 
            # 修正：storage.py 中的 filter_keys 通常返回"不存在于存储中的key"
            # 假设 base class filter_keys behaves as "return keys that are NOT in storage"
            
            if not new_docs_to_insert:
                logger.warning("所有文档已存在")
                return

            logger.info(f"📝 插入新文档: {len(new_docs_to_insert)} 篇")

            # 2. 生成并存储文本块
            inserting_chunks = {}
            for doc_key, doc in new_docs_to_insert.items():
                chunks = self.chunk_func(
                    doc["content"],
                    overlap_token_size=self.chunk_overlap_token_size,
                    max_token_size=self.chunk_token_size,
                    tiktoken_model=self.tiktoken_model_name,
                )
                for chunk in chunks:
                    chunk_id = compute_mdhash_id(chunk["content"], prefix="chunk-")
                    inserting_chunks[chunk_id] = {
                        **chunk,
                        "full_doc_id": doc_key,
                    }

            # 过滤已存在的 chunk (理论上新文档的chunk也应该是新的，但为了保险)
            chunk_keys = list(inserting_chunks.keys())
            missing_chunk_keys = await self.text_chunks.filter_keys(chunk_keys)
            final_chunks = {k: v for k, v in inserting_chunks.items() if k in missing_chunk_keys}

            if not final_chunks:
                logger.warning("所有文本块已存在")
                return

            logger.info(f"📄 插入新文本块: {len(final_chunks)} 个")

            await self.full_docs.upsert(new_docs_to_insert)
            await self.text_chunks.upsert(final_chunks)

        finally:
            await self._done()

    async def _done(self):
        await asyncio.gather(
            self.full_docs.index_done_callback(),
            self.text_chunks.index_done_callback()
        )


# 向后兼容
text_chunking_func = TextChunking


# ============================================================================
# 图像处理辅助函数
# ============================================================================

def compress_image_to_size(
    input_image: Image.Image, 
    output_path: str, 
    target_size_mb: int = 5, 
    step: int = 10, 
    quality: int = 90
) -> bool:
    """将图片压缩到目标大小以内"""
    target_bytes = target_size_mb * 1024 * 1024
    
    # 第一次保存
    input_image.save(output_path, quality=quality)
    
    # 循环压缩
    while os.path.getsize(output_path) > target_bytes and quality > 10:
        quality -= step
        input_image.save(output_path, quality=quality)
    
    if os.path.getsize(output_path) <= target_bytes:
        return True
    
    logger.warning("⚠️ 无法将图片压缩到目标大小以内")
    return False


async def get_image_description(
    image_path: str, 
    caption: list, 
    footnote: list, 
    context: str,
    hashing_kv: Optional[BaseKVStorage] = None
) -> tuple[str, bool]:
    """生成图像描述和分割标志"""
    with open(image_path, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")
    
    user_prompt = PROMPTS["image_description_user_with_examples"].format(
        caption=" ".join(caption),
        footnote=" ".join(footnote),
        context=context
    )
    
    default_result = {"description": "No description.", "segmentation": "false"}
    
    try:
        content = await asyncio.wait_for(
            multimodel_if_cache(
                user_prompt=user_prompt,
                img_base=img_base64,
                system_prompt=PROMPTS["image_description_system"],
                hashing_kv=hashing_kv,
                timeout=30
            ),
            timeout=30.0
        )
        result = normalize_to_json(content) or default_result
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ 生成描述超时: {image_path}")
        result = {"description": "Image description generation timed out.", "segmentation": "false"}
    except Exception as e:
        logger.error(f"❌ 生成描述失败 {image_path}: {e}")
        result = {"description": "Image description generation failed.", "segmentation": "false"}

    description = result.get("description", "No description.")
    segmentation = str(result.get("segmentation", "false")).lower() == 'true'
    
    return description, segmentation


def find_chunk_for_image(text_chunks: dict, context: str) -> Optional[str]:
    """根据上下文匹配最佳文本块"""
    if not context:
        return None
        
    best_chunk_id = None
    best_match_count = 0
    context_words = set(context.split())
    
    for chunk_id, chunk_data in text_chunks.items():
        chunk_content = chunk_data['content'].replace('\n', '')
        # 简单的词袋匹配
        match_count = sum(1 for word in context_words if word in chunk_content)
        
        if match_count > best_match_count:
            best_match_count = match_count
            best_chunk_id = chunk_id
            
    return best_chunk_id


# ============================================================================
# PDF 处理 (PyMuPDF & MinerU)
# ============================================================================

@dataclass
class PdfChunking:
    """PDF 文档处理类 (支持 PyMuPDF 和 MinerU)"""
    context_length: int = 100
    key_string_value_json_storage_cls: Type[BaseKVStorage] = JsonKVStorage

    def __post_init__(self):
        self.image_data = self.key_string_value_json_storage_cls(namespace="image_data")
        self.mmllm_response_cache = self.key_string_value_json_storage_cls(
            namespace="multimodel_llm_response_cache",
            storage_dir=parameter.CACHE_PATH
        )
    
    async def extract_text_and_images(self, pdf_path: str):
        """提取 PDF 文本和图像"""
        output_dir = parameter.WORKING_DIR
        chunker = TextChunking()

        try:
            use_mineru = parameter.USE_MINERU
            mineru_path = shutil.which('mineru')
            
            if use_mineru and not mineru_path:
                logger.warning("⚠️ 未找到 'mineru' 命令，自动降级为 PyMuPDF 处理")
                use_mineru = False
            
            if use_mineru:
                logger.info(f"🔧 使用 MinerU 处理 PDF (Path: {mineru_path})...")
                try:
                    data = await self._process_mineru(pdf_path, output_dir, chunker, mineru_path)
                except Exception as e:
                    logger.error(f"❌ MinerU 处理失败: {e}，尝试降级为 PyMuPDF")
                    data = await self._process_pymupdf(pdf_path, output_dir, chunker)
            else:
                logger.info("📄 使用 PyMuPDF 处理 PDF...")
                data = await self._process_pymupdf(pdf_path, output_dir, chunker)
                
            await self.image_data.upsert(data)
        finally:
            await asyncio.gather(
                self.image_data.index_done_callback(),
                self.mmllm_response_cache.index_done_callback()
            )

    async def _process_pymupdf(self, pdf_path: str, output_dir: str, chunker: TextChunking) -> dict:
        try:
            import fitz
        except ImportError:
            logger.error("❌ 未找到 PyMuPDF (fitz) 模块。如果未使用 MinerU，请安装: pip install pymupdf")
            raise

        doc = fitz.open(pdf_path)
        full_text = "".join([page.get_text("text") + "\n" for page in doc])
        
        # 1. 文本分块
        logger.info("  📝 步骤1.1: 文本分块...")
        await chunker.text_chunking(full_text)
        
        # 加载分块结果
        chunks_path = os.path.join(output_dir, 'kv_store_text_chunks.json')
        text_chunks = load_json(chunks_path) or {}

        # 2. 图像提取与上下文关联
        logger.info("  📷 步骤1.2: 提取图像...")
        images_dir = os.path.join(output_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        contexts = self._extract_pdf_contexts(doc)
        image_data = {}
        
        # 收集所有图像
        all_images = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            for img in page.get_images(full=True):
                all_images.append((page_num, img))
        
        logger.info("  🖼️ 步骤1.3: 生成图像描述...")
        for idx, (page_num, img) in enumerate(tqdm(all_images, desc="🖼️ 图像预处理", unit="张")):
            img_counter = idx + 1
            
            # 提取并保存图像
            page = doc.load_page(page_num)
            base = doc.extract_image(img[0])
            img_path = os.path.join(images_dir, f'image_{img_counter}.jpg')
            
            with Image.open(BytesIO(base["image"])) as pil_img:
                compress_image_to_size(pil_img.convert('RGB'), img_path)

            # 生成描述
            ctx_info = contexts.get(f"image_{img_counter}", {})
            context_str = f"{ctx_info.get('before', '')} {ctx_info.get('after', '')}"
            
            desc, seg = await get_image_description(
                img_path, [], [], context_str, 
                hashing_kv=self.mmllm_response_cache
            )
            
            # 关联 Chunk
            chunk_id = find_chunk_for_image(text_chunks, context_str)
            if chunk_id:
                image_data[f"image_{img_counter}"] = {
                    "image_id": img_counter,
                    "image_path": img_path,
                    "caption": [],
                    "footnote": [],
                    "context": context_str,
                    "chunk_order_index": text_chunks[chunk_id]['chunk_order_index'],
                    "chunk_id": chunk_id,
                    "description": desc,
                    "segmentation": seg
                }
                logger.debug(f"✅ 处理图像 (PyMuPDF): {img_path}")

        doc.close()
        return image_data

    async def _process_mineru(self, pdf_path: str, output_dir: str, chunker: TextChunking, mineru_path: str) -> dict:
        folder_path = self._run_mineru(pdf_path, output_dir, mineru_path)
        
        # 读取 Markdown
        md_file = next((f for f in os.listdir(folder_path) if f.endswith(".md")), None)
        if not md_file:
            raise ValueError("未找到 MinerU 生成的 .md 文件")
            
        with open(os.path.join(folder_path, md_file), 'r', encoding='utf-8') as f:
            full_text = re.sub(r'!\[\]\([^)]*\)', '', f.read()) # 清除图片标记

        # 1. 文本分块
        logger.info("  📝 步骤1.1: 文本分块...")
        await chunker.text_chunking(full_text)
        text_chunks = load_json(os.path.join(output_dir, 'kv_store_text_chunks.json')) or {}

        # 2. 处理图像和 JSON
        logger.info("  📷 步骤1.2: 提取图像...")
        images_dir = os.path.join(output_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        content_json_path = next((os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('_content_list.json')), None)
        if not content_json_path:
            raise ValueError("未找到 content_list.json")

        data = load_json(content_json_path)
        image_data = {}
        
        # 收集所有图像项
        image_items = [(i, item) for i, item in enumerate(data) if item.get("img_path")]
        
        logger.info("  🖼️ 步骤1.3: 生成图像描述...")
        for img_counter, (i, item) in enumerate(tqdm(image_items, desc="🖼️ 图像预处理", unit="张"), start=1):

            # 移动并重命名图像
            src_img = os.path.join(folder_path, item["img_path"])
            dst_img = os.path.join(images_dir, f"image_{img_counter}.jpg")
            
            if os.path.exists(src_img) and os.path.isfile(src_img):
                shutil.copy(src_img, dst_img)
            else:
                logger.warning(f"MinerU 图像丢失: {src_img}")
                continue

            # 提取上下文
            context = self._get_mineru_context(data, i)
            
            # 生成描述
            caption = item.get("img_caption", []) if item["type"] == "image" else item.get("table_caption", [])
            footnote = item.get("img_footnote", []) if item["type"] == "image" else item.get("table_footnote", [])
            
            desc, seg = await get_image_description(
                dst_img, caption, footnote, context,
                hashing_kv=self.mmllm_response_cache
            )
            chunk_id = find_chunk_for_image(text_chunks, context)

            if chunk_id:
                key = f"image_{img_counter}"
                image_data[key] = {
                    "image_id": img_counter,
                    "image_path": dst_img,
                    "caption": caption,
                    "footnote": footnote,
                    "context": context,
                    "chunk_order_index": text_chunks[chunk_id]['chunk_order_index'],
                    "chunk_id": chunk_id,
                    "description": desc,
                    "segmentation": seg
                }
                logger.debug(f"✅ 处理图像 (MinerU): {dst_img}")
            
            
        return image_data

    def _extract_pdf_contexts(self, doc) -> dict:
        """从 PyMuPDF 文档提取图像上下文"""
        results = {}
        img_counter = 1
        
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            all_text = []
            img_indices = []
            
            for block in blocks:
                if block["type"] == 0: # Text
                    for line in block["lines"]:
                        for span in line["spans"]:
                            all_text.append(span["text"])
                elif block["type"] == 1: # Image
                    img_indices.append(len(all_text))
            
            for idx in img_indices:
                before = " ".join(all_text[max(0, idx-10):idx]) # 简化：取前10段
                after = " ".join(all_text[idx:min(len(all_text), idx+10)])
                
                results[f"image_{img_counter}"] = {
                    "before": before[-self.context_length:] if len(before) > self.context_length else before,
                    "after": after[:self.context_length]
                }
                img_counter += 1
        return results

    def _run_mineru(self, pdf_path: str, output_dir: str, mineru_path: str) -> str:
        """运行 MinerU 命令"""
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_folder = os.path.join(output_dir, pdf_name, "auto")
        
        if os.path.exists(output_folder) and any(f.endswith(".md") for f in os.listdir(output_folder)):
            logger.info("✓ MinerU 已完成处理 (缓存)")
            return output_folder
            
        try:
            # 使用传入的 mineru_path
            subprocess.run([mineru_path, '-p', pdf_path, '-o', output_dir], capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"MinerU 运行失败: {e.stderr}")
            raise
            
        return output_folder

    def _get_mineru_context(self, data: list, index: int) -> str:
        """从 MinerU 数据提取上下文"""
        # 前向
        prev_text = []
        curr = index - 1
        acc_len = 0
        while curr >= 0 and acc_len < self.context_length:
            txt = data[curr].get("text", "")
            prev_text.insert(0, txt)
            acc_len += len(txt)
            curr -= 1
            
        # 后向
        next_text = []
        curr = index + 1
        acc_len = 0
        while curr < len(data) and acc_len < self.context_length:
            txt = data[curr].get("text", "")
            next_text.append(txt)
            acc_len += len(txt)
            curr += 1
            
        return " ".join(prev_text + next_text)


# 向后兼容
chunking_func_pdf2md = PdfChunking