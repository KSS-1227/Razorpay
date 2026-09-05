"""
存储模块 - 提供键值存储和图存储的抽象接口及实现

包含:
- TextChunkSchema: 文本块数据结构
- StorageNameSpace: 存储基类
- BaseKVStorage / JsonKVStorage: 键值存储抽象及JSON实现
- BaseGraphStorage / NetworkXStorage: 图存储抽象及NetworkX实现
"""
from dataclasses import dataclass
from typing import TypedDict, Union, Generic, TypeVar
import networkx as nx
import os

from .base import logger, load_json, write_json
from .. import parameter


# ============================================================================
# 数据类型定义
# ============================================================================

TextChunkSchema = TypedDict(
    "TextChunkSchema",
    {"tokens": int, "content": str, "full_doc_id": str, "chunk_order_index": int},
)
"""文本块数据结构，包含token数、内容、文档ID和块序号"""

T = TypeVar("T")  # 泛型类型变量


# ============================================================================
# 存储基类
# ============================================================================

@dataclass
class StorageNameSpace:
    """
    存储命名空间基类。
    
    Attributes:
        namespace: 命名空间名称，用于区分不同存储实例
        storage_dir: 存储目录路径，默认使用 WORKING_DIR
    """
    namespace: str
    storage_dir: str = None

    async def index_done_callback(self):
        """索引完成后的回调，用于持久化数据"""
        pass

    async def query_done_callback(self):
        """查询完成后的回调"""
        pass


# ============================================================================
# 键值存储
# ============================================================================

@dataclass
class BaseKVStorage(Generic[T], StorageNameSpace):
    """
    键值存储抽象基类。
    
    提供基本的CRUD操作接口，子类需实现具体存储逻辑。
    """
    
    async def all_keys(self) -> list[str]:
        """获取所有键"""
        raise NotImplementedError

    async def get_by_id(self, id: str) -> Union[T, None]:
        """根据ID获取单条数据"""
        raise NotImplementedError

    async def get_by_ids(
        self, ids: list[str], fields: Union[set[str], None] = None
    ) -> list[Union[T, None]]:
        """根据ID列表批量获取数据，可指定返回字段"""
        raise NotImplementedError

    async def filter_keys(self, data: list[str]) -> set[str]:
        """过滤出不存在的键"""
        raise NotImplementedError

    async def upsert(self, data: dict[str, T]):
        """插入或更新数据"""
        raise NotImplementedError

    async def drop(self):
        """清空存储"""
        raise NotImplementedError


@dataclass
class JsonKVStorage(BaseKVStorage):
    """
    基于JSON文件的键值存储实现。
    
    数据存储在 {storage_dir}/kv_store_{namespace}.json
    """
    
    def __post_init__(self):
        working_dir = self.storage_dir or parameter.WORKING_DIR
        self._file_name = os.path.join(working_dir, f"kv_store_{self.namespace}.json")
        self._data = load_json(self._file_name) or {}
        logger.info(f"💾 加载 {self.namespace}：{len(self._data)} 条数据")

    async def all_keys(self) -> list[str]:
        return list(self._data.keys())

    async def index_done_callback(self):
        write_json(self._data, self._file_name)

    async def get_by_id(self, id: str):
        return self._data.get(id, None)

    async def get_by_ids(self, ids: list[str], fields: set[str] = None):
        if fields is None:
            return [self._data.get(id) for id in ids]
        return [
            {k: v for k, v in self._data[id].items() if k in fields}
            if id in self._data else None
            for id in ids
        ]

    async def filter_keys(self, data: list[str]) -> set[str]:
        return {key for key in data if key not in self._data}

    async def upsert(self, data: dict[str, dict]):
        self._data.update(data)

    async def drop(self):
        self._data = {}


# ============================================================================
# 图存储
# ============================================================================

@dataclass
class BaseGraphStorage(StorageNameSpace):
    """
    图存储抽象基类。
    
    提供图的节点和边操作接口，子类需实现具体存储逻辑。
    """
    
    async def has_node(self, node_id: str) -> bool:
        """检查节点是否存在"""
        raise NotImplementedError

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """检查边是否存在"""
        raise NotImplementedError

    async def node_degree(self, node_id: str) -> int:
        """获取节点度数"""
        raise NotImplementedError

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        """获取边两端节点的度数之和"""
        raise NotImplementedError

    async def get_node(self, node_id: str) -> Union[dict, None]:
        """获取节点数据"""
        raise NotImplementedError

    async def get_edge(
        self, source_node_id: str, target_node_id: str
    ) -> Union[dict, None]:
        """获取边数据"""
        raise NotImplementedError

    async def get_node_edges(
        self, source_node_id: str
    ) -> Union[list[tuple[str, str]], None]:
        """获取节点的所有边"""
        raise NotImplementedError

    async def upsert_node(self, node_id: str, node_data: dict[str, str]):
        """插入或更新节点"""
        raise NotImplementedError

    async def upsert_edge(
        self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]
    ):
        """插入或更新边"""
        raise NotImplementedError


@dataclass
class NetworkXStorage(BaseGraphStorage):
    """
    基于NetworkX的图存储实现。
    
    数据存储在 {storage_dir}/graph_{namespace}.graphml
    """
    
    # -------------------- 静态工具方法 --------------------
    
    @staticmethod
    def load_nx_graph(file_name: str) -> nx.Graph:
        """从GraphML文件加载图"""
        if os.path.exists(file_name):
            return nx.read_graphml(file_name)
        return None

    @staticmethod
    def write_nx_graph(graph: nx.Graph, file_name: str):
        """将图写入GraphML文件"""
        logger.info(f"📊 写入图谱: {len(graph.nodes())} 个节点, {len(graph.edges())} 条边")
        nx.write_graphml(graph, file_name)

    @staticmethod
    def _stabilize_graph(graph: nx.Graph) -> nx.Graph:
        """
        稳定化图结构，确保相同数据产生相同的序列化结果。
        
        - 节点按名称排序
        - 边的源/目标按字典序排列（无向图）
        - 边按 "source -> target" 格式排序
        """
        fixed_graph = nx.DiGraph() if graph.is_directed() else nx.Graph()
        
        # 排序并添加节点
        sorted_nodes = sorted(graph.nodes(data=True), key=lambda x: x[0])
        fixed_graph.add_nodes_from(sorted_nodes)
        
        # 处理边
        edges = list(graph.edges(data=True))
        if not graph.is_directed():
            # 无向图：确保 source < target
            edges = [
                (min(s, t), max(s, t), d) for s, t, d in edges
            ]
        
        # 排序并添加边
        edges = sorted(edges, key=lambda x: f"{x[0]} -> {x[1]}")
        fixed_graph.add_edges_from(edges)
        
        return fixed_graph

    # -------------------- 实例方法 --------------------
    
    def __post_init__(self):
        working_dir = self.storage_dir or parameter.WORKING_DIR
        self._graphml_xml_file = os.path.join(
            working_dir, f"graph_{self.namespace}.graphml"
        )
        preloaded_graph = NetworkXStorage.load_nx_graph(self._graphml_xml_file)
        if preloaded_graph is not None:
            logger.info(
                f"📥 已加载图谱: {self._graphml_xml_file}, "
                f"{len(preloaded_graph.nodes())} 个节点, "
                f"{len(preloaded_graph.edges())} 条边"
            )
        self._graph = preloaded_graph or nx.Graph()

    async def index_done_callback(self):
        NetworkXStorage.write_nx_graph(self._graph, self._graphml_xml_file)

    async def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        return self._graph.has_edge(source_node_id, target_node_id)

    async def get_node(self, node_id: str) -> Union[dict, None]:
        return self._graph.nodes.get(node_id)

    async def node_degree(self, node_id: str) -> int:
        return self._graph.degree(node_id) if self._graph.has_node(node_id) else 0

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        src_deg = self._graph.degree(src_id) if self._graph.has_node(src_id) else 0
        tgt_deg = self._graph.degree(tgt_id) if self._graph.has_node(tgt_id) else 0
        return src_deg + tgt_deg

    async def get_edge(
        self, source_node_id: str, target_node_id: str
    ) -> Union[dict, None]:
        return self._graph.edges.get((source_node_id, target_node_id))

    async def get_node_edges(self, source_node_id: str):
        if self._graph.has_node(source_node_id):
            return list(self._graph.edges(source_node_id))
        return None

    async def upsert_node(self, node_id: str, node_data: dict[str, str]):
        self._graph.add_node(node_id, **node_data)

    async def upsert_edge(
        self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]
    ):
        self._graph.add_edge(source_node_id, target_node_id, **edge_data)