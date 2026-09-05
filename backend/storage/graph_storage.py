"""
Graph storage abstraction and NetworkX-backed implementation.
"""
import os
from dataclasses import dataclass

import networkx as nx

from ..config import settings as parameter
from ..utils.base import logger
from .kv_storage import StorageNameSpace


@dataclass
class BaseGraphStorage(StorageNameSpace):

    async def has_node(self, node_id: str) -> bool:
        raise NotImplementedError

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        raise NotImplementedError

    async def node_degree(self, node_id: str) -> int:
        raise NotImplementedError

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        raise NotImplementedError

    async def get_node(self, node_id: str) -> dict | None:
        raise NotImplementedError

    async def get_edge(self, source_node_id: str, target_node_id: str) -> dict | None:
        raise NotImplementedError

    async def get_node_edges(self, source_node_id: str) -> list[tuple[str, str]] | None:
        raise NotImplementedError

    async def upsert_node(self, node_id: str, node_data: dict[str, str]):
        raise NotImplementedError

    async def upsert_edge(self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]):
        raise NotImplementedError


@dataclass
class NetworkXStorage(BaseGraphStorage):

    @staticmethod
    def load_nx_graph(file_name: str) -> nx.Graph:
        if os.path.exists(file_name):
            return nx.read_graphml(file_name)
        return None

    @staticmethod
    def write_nx_graph(graph: nx.Graph, file_name: str):
        logger.info(f"📊 Writing graph: {len(graph.nodes())} nodes, {len(graph.edges())} edges")
        nx.write_graphml(graph, file_name)

    @staticmethod
    def _stabilize_graph(graph: nx.Graph) -> nx.Graph:
        fixed_graph = nx.DiGraph() if graph.is_directed() else nx.Graph()
        sorted_nodes = sorted(graph.nodes(data=True), key=lambda x: x[0])
        fixed_graph.add_nodes_from(sorted_nodes)
        edges = list(graph.edges(data=True))
        if not graph.is_directed():
            edges = [(min(s, t), max(s, t), d) for s, t, d in edges]
        edges = sorted(edges, key=lambda x: f"{x[0]} -> {x[1]}")
        fixed_graph.add_edges_from(edges)
        return fixed_graph

    def __post_init__(self):
        working_dir = self.storage_dir or parameter.WORKING_DIR
        self._graphml_xml_file = os.path.join(working_dir, f"graph_{self.namespace}.graphml")
        preloaded_graph = NetworkXStorage.load_nx_graph(self._graphml_xml_file)
        if preloaded_graph is not None:
            logger.info(
                f"📥 Graph loaded: {self._graphml_xml_file}, "
                f"{len(preloaded_graph.nodes())} nodes, "
                f"{len(preloaded_graph.edges())} edges"
            )
        self._graph = preloaded_graph or nx.Graph()

    async def index_done_callback(self):
        NetworkXStorage.write_nx_graph(self._graph, self._graphml_xml_file)

    async def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        return self._graph.has_edge(source_node_id, target_node_id)

    async def get_node(self, node_id: str) -> dict | None:
        return self._graph.nodes.get(node_id)

    async def node_degree(self, node_id: str) -> int:
        return self._graph.degree(node_id) if self._graph.has_node(node_id) else 0

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        src_deg = self._graph.degree(src_id) if self._graph.has_node(src_id) else 0
        tgt_deg = self._graph.degree(tgt_id) if self._graph.has_node(tgt_id) else 0
        return src_deg + tgt_deg

    async def get_edge(self, source_node_id: str, target_node_id: str) -> dict | None:
        return self._graph.edges.get((source_node_id, target_node_id))

    async def get_node_edges(self, source_node_id: str):
        if self._graph.has_node(source_node_id):
            return list(self._graph.edges(source_node_id))
        return None

    async def upsert_node(self, node_id: str, node_data: dict[str, str]):
        self._graph.add_node(node_id, **node_data)

    async def upsert_edge(self, source_node_id: str, target_node_id: str, edge_data: dict[str, str]):
        self._graph.add_edge(source_node_id, target_node_id, **edge_data)
