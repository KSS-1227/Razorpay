"""
Flask visualization server — serves the graph explorer UI and REST API.
"""
import os
import xml.etree.ElementTree as ET

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from ..config import settings as parameter

app = Flask(__name__, static_folder=os.path.dirname(__file__))
CORS(app)

_GRAPH_PATH = None


def run_visualization_server(
    graph_path: str | None = None,
    host: str = "0.0.0.0",
    port: int = 5000,
):
    global _GRAPH_PATH
    _GRAPH_PATH = graph_path or os.path.join(
        parameter.OUTPUT_DIR, f"{parameter.MMKG_NAME}.graphml"
    )
    print(f"🌐  Graph Explorer → http://localhost:{port}")
    app.run(host=host, port=port, debug=False)


def _get_graph_path():
    return _GRAPH_PATH or os.path.join(
        parameter.OUTPUT_DIR, f"{parameter.MMKG_NAME}.graphml"
    )


def _parse_graph():
    path = _get_graph_path()
    if not os.path.exists(path):
        return None, None
    tree = ET.parse(path)
    root = tree.getroot()
    ns   = {"g": "http://graphml.graphdrawing.org/xmlns"}
    return root, ns


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "graph_explorer.html")


@app.route("/api/graph/info")
def graph_info():
    root, ns = _parse_graph()
    if root is None:
        return jsonify({"error": "Graph not found"}), 404

    nodes = root.findall(".//g:node", ns)
    edges = root.findall(".//g:edge", ns)

    type_counts = {}
    for node in nodes:
        etype = ""
        for d in node.findall("g:data", ns):
            if d.get("key") == "d0":
                etype = (d.text or "").strip('"')
        type_counts[etype] = type_counts.get(etype, 0) + 1

    return jsonify({
        "node_count": len(nodes),
        "edge_count": len(edges),
        "entity_types": type_counts,
    })


@app.route("/api/graph/content")
def graph_content():
    root, ns = _parse_graph()
    if root is None:
        return jsonify({"error": "Graph not found"}), 404

    page      = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 100))

    nodes_out = []
    for node in root.findall(".//g:node", ns):
        nid   = node.get("id", "")
        ndata = {"id": nid}
        for d in node.findall("g:data", ns):
            if d.get("key") == "d0":
                ndata["entity_type"] = (d.text or "").strip('"')
            if d.get("key") == "d1":
                ndata["description"] = d.text or ""
            if d.get("key") == "d2":
                ndata["source_id"]   = d.text or ""
        nodes_out.append(ndata)

    edges_out = []
    for edge in root.findall(".//g:edge", ns):
        edata = {"source": edge.get("source", ""), "target": edge.get("target", "")}
        for d in edge.findall("g:data", ns):
            if d.get("key") == "d3":
                edata["weight"]      = d.text or ""
            if d.get("key") == "d4":
                edata["description"] = d.text or ""
        edges_out.append(edata)

    start = (page - 1) * page_size
    return jsonify({
        "nodes": nodes_out[start: start + page_size],
        "edges": edges_out[start: start + page_size],
        "total_nodes": len(nodes_out),
        "total_edges": len(edges_out),
    })


@app.route("/api/graph/search")
def graph_search():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify([])
    root, ns = _parse_graph()
    if root is None:
        return jsonify([])

    results = []
    for node in root.findall(".//g:node", ns):
        nid = node.get("id", "")
        if query in nid.lower():
            ndata = {"id": nid}
            for d in node.findall("g:data", ns):
                if d.get("key") == "d0":
                    ndata["entity_type"] = (d.text or "").strip('"')
                if d.get("key") == "d1":
                    ndata["description"] = d.text or ""
            results.append(ndata)
        if len(results) >= 20:
            break
    return jsonify(results)


@app.route("/api/graph/retrieve")
def graph_retrieve():
    query = request.args.get("q", "")
    top_k = int(request.args.get("top_k", 10))
    if not query:
        return jsonify([])

    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        embed_model  = parameter.get_embed_model()
        embed_path   = os.path.join(parameter.OUTPUT_DIR, f"{parameter.MMKG_NAME}_emb.npy")
        graph_path   = _get_graph_path()

        import networkx as nx
        G        = nx.read_graphml(graph_path)
        nodes    = list(G.nodes())
        descs    = [G.nodes[n].get("description", n) for n in nodes]

        if os.path.exists(embed_path):
            embeddings = np.load(embed_path)
        else:
            embeddings = embed_model.encode(descs)

        q_emb = embed_model.encode([query])
        sims  = cosine_similarity(q_emb, embeddings)[0]
        idxs  = np.argsort(sims)[::-1][:top_k]

        return jsonify([
            {"id": nodes[i], "score": float(sims[i]),
             "entity_type": G.nodes[nodes[i]].get("entity_type", ""),
             "description": G.nodes[nodes[i]].get("description", "")}
            for i in idxs
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
