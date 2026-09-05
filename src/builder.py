"""
多模态知识图谱构建器

从PDF文档构建多模态知识图谱，支持文本和图像的实体提取与融合。

主要流程:
1. PDF预处理 (MinerU提取文本和图像)
2. 文本实体提取
3. 图像实体提取
4. 知识图谱融合
5. 保存最终GraphML文件
6. 生成统计报告

使用示例:
    builder = MMKGBuilder(working_dir="./output")
    builder.index("path/to/document.pdf")
"""

import asyncio
import os
import shutil
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import networkx as nx

from . import parameter
from .core.base import check_json_not_empty, get_latest_graphml_file, load_json, logger
from .parameter import CACHE_PATH, OUTPUT_DIR


# ============================================================================
# 初始化
# ============================================================================

# 确保cache路径存在
_cache_path = parameter.CACHE_PATH or "cache"
os.makedirs(_cache_path, exist_ok=True)
os.environ['CACHE_PATH'] = _cache_path


def _get_event_loop() -> asyncio.AbstractEventLoop:
    """获取或创建事件循环"""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        logger.info("在子线程中创建新事件循环")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


# ============================================================================
# 构建器
# ============================================================================

@dataclass
class MMKGBuilder:
    """
    多模态知识图谱构建器
    
    Attributes:
        working_dir: 工作目录路径，默认使用 parameter.WORKING_DIR
    """
    working_dir: str = None

    def __post_init__(self):
        # 设置工作目录
        if self.working_dir is None:
            self.working_dir = parameter.WORKING_DIR or "working"
        parameter.WORKING_DIR = self.working_dir
        
        # 确保工作目录存在
        os.makedirs(self.working_dir, exist_ok=True)
        logger.info(f"工作目录: {self.working_dir}")
        
        # 打印配置
        self._log_config()
        
        # 初始化核心组件
        from .preprocessing import chunking_func_pdf2md
        from .graph.text2graph import TextEntityExtractor
        
        self.preprocessing = chunking_func_pdf2md()
        self.text_extractor = TextEntityExtractor()

    def _log_config(self):
        """打印配置信息"""
        config = {
            "working_dir": self.working_dir,
            "entity_extract_max_gleaning": parameter.ENTITY_EXTRACT_MAX_GLEANING,
            "entity_summary_max_tokens": parameter.ENTITY_SUMMARY_MAX_TOKENS,
            "summary_context_max_tokens": parameter.SUMMARY_CONTEXT_MAX_TOKENS,
            "use_mineru": parameter.USE_MINERU,
        }
        config_str = ", ".join(f"{k}={v}" for k, v in config.items())
        logger.debug(f"MMKGBuilder config: {config_str}")

    # -------------------- 公开接口 --------------------

    def index(self, pdf_path: str):
        """同步接口：构建知识图谱"""
        return _get_event_loop().run_until_complete(self.aindex(pdf_path))

    async def aindex(self, pdf_path: str):
        """
        异步接口：构建知识图谱
        
        Args:
            pdf_path: PDF文件路径
        """
        from .graph.fusion import fusion
        from .graph.img2graph import img2graph

        start_time = time.time()
        start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 生成图谱名称（如未指定则使用时间戳）
        self.mmkg_name = parameter.MMKG_NAME or f"mmkg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.pdf_path = pdf_path
        
        # 构建过程统计信息
        self.build_stats = {
            "text_chunks": 0,
            "images": 0,
            "text_entities": 0,
            "image_entities": 0,
            "pre_fusion_nodes": 0,
            "post_fusion_nodes": 0,
        }

        logger.info("=" * 60)
        logger.info("开始构建多模态知识图谱")
        logger.info(f"图谱名称: {self.mmkg_name}")
        logger.info("=" * 60)

        # 步骤1: PDF预处理
        await self._step_preprocessing(pdf_path)
        
        # 步骤2: 文本实体提取
        await self._step_text_extraction()
        
        # 步骤3: 图像实体提取
        await self._step_image_extraction(img2graph)
        
        # 步骤4: 知识图谱融合
        await self._step_fusion(fusion)
        
        # 步骤5: 保存最终图谱
        self._step_save_output()

        # 步骤6: 生成统计报告
        end_time = time.time()
        duration = end_time - start_time
        self._step_generate_report(start_datetime, duration)

        logger.info("=" * 60)
        logger.info(f"✓ 知识图谱构建完成，输出目录: {OUTPUT_DIR}")
        logger.info(f"✓ 图谱文件: {self.mmkg_name}.graphml")
        logger.info("=" * 60)

    # -------------------- 处理步骤 --------------------

    async def _step_preprocessing(self, pdf_path: str):
        """步骤1: PDF预处理"""
        logger.info("\n► 步骤1: PDF预处理")
        
        kv_store_img = os.path.join(self.working_dir, "kv_store_image_data.json")
        kv_store_text = os.path.join(self.working_dir, "kv_store_text_chunks.json")
        
        if check_json_not_empty(kv_store_img) and check_json_not_empty(kv_store_text):
            logger.info("✓ 检测到已有预处理数据，跳过")
            return
        
        await self.preprocessing.extract_text_and_images(pdf_path)
        
        # 收集统计信息
        chunks_path = os.path.join(self.working_dir, "kv_store_text_chunks.json")
        chunks = load_json(chunks_path) or {}
        self.build_stats["text_chunks"] = len(chunks)
        
        img_folder = os.path.join(self.working_dir, "images")
        if os.path.exists(img_folder):
            self.build_stats["images"] = len([f for f in os.listdir(img_folder) if f.endswith('.jpg')])
        
        logger.info(f"✓ PDF预处理完成（文本块: {self.build_stats['text_chunks']}，图像: {self.build_stats['images']}）")

    async def _step_text_extraction(self):
        """步骤2: 文本实体提取"""
        logger.info("\n► 步骤2: 文本实体提取")
        

        graph_path = os.path.join(self.working_dir, "graph_chunk_entity_relation.graphml")
        if os.path.exists(graph_path):
            try:
                G = nx.read_graphml(graph_path)
                if G.number_of_nodes() > 0:
                    logger.info(f"✓ 检测到文本实体图谱（{G.number_of_nodes()} 节点），跳过")
                    return
                logger.warning("⚠️ 文本实体图谱为空，重新提取")
            except Exception:
                logger.warning("⚠️ 文本实体图谱损坏，重新提取")
        
        chunks_path = os.path.join(self.working_dir, "kv_store_text_chunks.json")
        chunks = load_json(chunks_path)
        
        await self.text_extractor.text_entity_extraction(chunks)
        
        # 收集实体统计
        if os.path.exists(graph_path):
            G = nx.read_graphml(graph_path)
            self.build_stats["text_entities"] = G.number_of_nodes()
            self.build_stats["pre_fusion_nodes"] = G.number_of_nodes()
        
        logger.info(f"✓ 文本实体提取完成（实体数: {self.build_stats['text_entities']}）")

    async def _step_image_extraction(self, img2graph_func):
        """步骤3: 图像实体提取"""
        logger.info("\n► 步骤3: 图像实体提取")
        
        img_folder = os.path.join(self.working_dir, "images")
        
        if not os.path.exists(img_folder):
            logger.info("未检测到图像文件夹，跳过")
            return
        
        # img2graph 内部会自动跳过已处理的图片
        await img2graph_func(img_folder)
        
        # 统计图像实体
        image_graphs = [f for f in os.listdir(img_folder) if f.endswith('.graphml')]
        for subdir in os.listdir(img_folder):
            subdir_path = os.path.join(img_folder, subdir)
            if os.path.isdir(subdir_path):
                image_graphs.extend([f for f in os.listdir(subdir_path) if f.endswith('.graphml')])
        self.build_stats["image_entities"] = len(image_graphs)
        
        logger.info(f"✓ 图像实体提取完成（图像图谱: {self.build_stats['image_entities']}）")

    async def _step_fusion(self, fusion_func):
        """步骤4: 知识图谱融合"""
        logger.info("\n► 步骤4: 知识图谱融合")
        
        image_data_path = os.path.join(self.working_dir, "kv_store_image_data.json")
        image_data = load_json(image_data_path)
        
        if not image_data:
            logger.info("未检测到图片数据，跳过融合")
            return
        
        await fusion_func(list(image_data.keys()))
        logger.info("✓ 知识图谱融合完成")

    def _step_save_output(self):
        """步骤5: 保存最终图谱文件"""
        namespace, graphml_path = get_latest_graphml_file(self.working_dir)
        
        if not graphml_path or not os.path.exists(graphml_path):
            logger.warning(f"未找到GraphML文件: {self.working_dir}")
            return
        
        output_dir = parameter.OUTPUT_DIR or "output"
        os.makedirs(output_dir, exist_ok=True)
        target_path = os.path.join(output_dir, f"{self.mmkg_name}.graphml")
        shutil.copy2(graphml_path, target_path)
        
        # 统计融合后节点数
        G = nx.read_graphml(target_path)
        self.build_stats["post_fusion_nodes"] = G.number_of_nodes()
        
        logger.info(f"\n✓ 知识图谱已保存: {target_path}")

    def _step_generate_report(self, start_datetime: str, duration: float):
        """步骤6: 生成统计报告"""
        logger.info("\n► 步骤6: 生成统计报告")
        
        output_dir = parameter.OUTPUT_DIR or "output"
        target_graph_path = os.path.join(output_dir, f"{self.mmkg_name}.graphml")
        report_path = os.path.join(output_dir, f"{self.mmkg_name}_report.md")
        
        if not os.path.exists(target_graph_path):
            logger.warning("未找到最终图谱文件，无法生成报告")
            return

        try:
            G = nx.read_graphml(target_graph_path)
            
            # 基础统计
            num_nodes = G.number_of_nodes()
            num_edges = G.number_of_edges()
            density = nx.density(G)
            components = nx.number_connected_components(G) if not G.is_directed() else nx.number_weakly_connected_components(G)
            
            # 实体类型分布
            entity_types = []
            for _, data in G.nodes(data=True):
                etype = data.get("entity_type") or data.get("type") or "UNKNOWN"
                entity_types.append(etype.strip('"'))
            
            type_counts = Counter(entity_types)
            
            # 构建报告内容
            report_content = f"""# 多模态知识图谱构建报告

## 1. 构建概况
- **图谱名称**: `{self.mmkg_name}`
- **构建日期**: {start_datetime}
- **总耗时**: {duration:.2f} 秒
- **输出目录**: `{os.path.abspath(output_dir)}`

## 2. 参数配置
- **LLM 模型**: `{parameter.MODEL_NAME}`
- **多模态模型**: `{parameter.MM_MODEL_NAME}`
- **Embedding 模型**: `{os.path.basename(parameter.EMBEDDING_MODEL_DIR)}`
- **PDF 预处理**: `{'MinerU' if parameter.USE_MINERU else 'PyMuPDF'}`
- **工作目录**: `{self.working_dir}`

## 3. 构建过程记录

### 3.1 PDF预处理
- **输入文件**: `{os.path.basename(self.pdf_path)}`
- **预处理方法**: {'MinerU' if parameter.USE_MINERU else 'PyMuPDF'}
- **文本块数量**: {self.build_stats['text_chunks']}
- **图像数量**: {self.build_stats['images']}

### 3.2 实体提取
- **文本实体数**: {self.build_stats['text_entities']}
- **图像图谱数**: {self.build_stats['image_entities']}

### 3.3 知识图谱融合
- **融合前节点数**: {self.build_stats['pre_fusion_nodes']}
- **融合后节点数**: {self.build_stats['post_fusion_nodes']}

## 4. 图谱统计
- **节点总数**: {num_nodes}
- **边总数**: {num_edges}
- **图密度**: {density:.6f}
- **连通分量数**: {components}

### 实体类型分布
"""
            for etype, count in type_counts.most_common():
                report_content += f"- **{etype}**: {count}\n"
                
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
                
            logger.info(f"✓ 统计报告已生成: {report_path}")
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
