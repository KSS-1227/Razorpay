import asyncio

import networkx as nx

from backend.api.routes import graph as graph_routes


def test_graph_network_serializes_nodes_and_edges(monkeypatch):
    graph = nx.Graph()
    graph.add_node("A", entity_type="Person", label="Alice")
    graph.add_node("B", entity_type="Organization", label="Acme")
    graph.add_edge("A", "B", weight=2)

    monkeypatch.setattr(graph_routes, "_load_graph", lambda: graph)

    payload = asyncio.run(graph_routes.graph_network())

    assert payload["nodes"][0]["id"] == "A"
    assert payload["nodes"][0]["label"] == "Alice"
    assert payload["nodes"][0]["type"] == "Person"
    assert payload["edges"][0]["source"] == "A"
    assert payload["edges"][0]["target"] == "B"
    assert payload["edges"][0]["weight"] == 2
