"""
Knowledge-graph fusion: aligns image KGs with the text KG and merges them.
"""
import math
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

import base64
import xml.etree.ElementTree as ET

import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN
from tqdm import tqdm

from ..config import settings as parameter
from ..config.settings import get_embed_model
from ..core.prompt import GRAPH_FIELD_SEP, PROMPTS
from ..llm import (
    get_llm_response,
    get_mmllm_response,
    normalize_to_json,
    normalize_to_json_list,
)
from ..utils.base import ensure_quoted, load_json, logger

# ============================================================================
# Data loaders — accept explicit working_dir to support workspace isolation
# ============================================================================

def _get_json_path(filename: str, working_dir: str | None = None) -> str:
    base = working_dir or parameter.WORKING_DIR
    return os.path.join(base, filename)

def get_image_data(working_dir: str | None = None) -> dict:
    return load_json(_get_json_path("kv_store_image_data.json", working_dir)) or {}

def get_chunk_knowledge_graph(working_dir: str | None = None) -> dict:
    return load_json(_get_json_path("kv_store_chunk_knowledge_graph.json", working_dir)) or {}

def get_text_chunks(working_dir: str | None = None) -> dict:
    return load_json(_get_json_path("kv_store_text_chunks.json", working_dir)) or {}

# ============================================================================
# Context helpers
# ============================================================================

def get_nearby_chunks(data: dict, index: int) -> list[str]:
    indices = range(max(0, index - 1), min(len(data), index + 2))
    return [v.get("content") for v in data.values() if v.get("chunk_order_index") in indices]

def get_nearby_entities(data: dict, index: int) -> list[dict]:
    indices = range(max(0, index - 1), min(len(data), index + 2))
    entities = []
    for chunk_index in indices:
        entities.extend(
            {
                key: value
                for key, value in entity.items()
                if key != "source_id"
            }
            for entity in data.get(str(chunk_index), {}).get("entities", [])
        )
    return entities

def get_nearby_relationships(data: dict, index: int) -> list[dict]:
    indices = range(max(0, index - 1), min(len(data), index + 2))
    relationships = []
    for chunk_index in indices:
        relationships.extend(
            {
                key: value
                for key, value in relationship.items()
                if key != "source_id"
            }
            for relationship in data.get(str(chunk_index), {}).get("relationships", [])
        )
    return relationships

def _sanitize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    if embeddings.size == 0:
        return embeddings
    embeddings = np.nan_to_num(embeddings, nan=0.0, posinf=1e6, neginf=-1e6)
    embeddings = np.clip(embeddings, -10.0, 10.0)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    zero_mask = (norms < 1e-8)
    if zero_mask.any():
        logger.warning(f"⚠️ Found {zero_mask.sum()} zero/near-zero vector embeddings")
        embeddings[zero_mask.flatten()] = np.random.normal(0, 1e-6, size=(zero_mask.sum(), embeddings.shape[1]))
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / np.maximum(norms, 1e-8)
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=1.0, neginf=-1.0)
    return normalized.astype(np.float64)

# ============================================================================
# Spectral clustering
# ============================================================================

def _compute_spectral_labels(embeddings, entity_names, relationships):
    normalized_embeddings = _sanitize_embeddings(embeddings)
    raw_similarity = np.dot(normalized_embeddings, normalized_embeddings.T)
    similarity_matrix = (raw_similarity + 1.0) / 2.0
    similarity_matrix = np.nan_to_num(similarity_matrix, nan=0.0, posinf=1.0, neginf=0.0)

    for rel in sorted(relationships, key=lambda x: x.get("weight", 0), reverse=True):
        src, tgt = rel.get("src_id"), rel.get("tgt_id")
        if src not in entity_names or tgt not in entity_names:
            continue
        weight_raw = rel.get("weight")
        if weight_raw is None:
            continue
        try:
            boost = min(float(weight_raw), 50.0) / 100.0
        except (ValueError, TypeError):
            continue
        if not np.isfinite(boost):
            continue
        src_idx = entity_names.index(src)
        tgt_idx = entity_names.index(tgt)
        similarity_matrix[src_idx, tgt_idx] += boost
        similarity_matrix[tgt_idx, src_idx] += boost

    similarity_matrix = np.clip(similarity_matrix, 0.0, 1.5)
    similarity_matrix = (similarity_matrix + similarity_matrix.T) / 2.0
    degree_matrix = np.diag(np.sum(similarity_matrix, axis=1))
    degree_matrix = np.clip(degree_matrix, 0, 1e6)
    laplacian_matrix = degree_matrix - similarity_matrix
    laplacian_matrix = np.nan_to_num(laplacian_matrix, nan=0.0, posinf=0.0, neginf=0.0)
    laplacian_matrix = (laplacian_matrix + laplacian_matrix.T) / 2.0

    try:
        eigvals, eigvecs = np.linalg.eigh(laplacian_matrix)
    except np.linalg.LinAlgError:
        logger.warning("⚠️ Laplacian matrix eigen-decomposition failed, falling back to eig")
        eigvals, eigvecs = np.linalg.eig(laplacian_matrix)

    eigvals = np.real(eigvals)
    eigvecs = np.real(eigvecs)
    idx = np.argsort(eigvals)
    eigvecs = eigvecs[:, idx]
    k = max(2, math.ceil(math.sqrt(len(entity_names))))
    eigvecs_selected = _sanitize_embeddings(eigvecs[:, :k])
    min_samples = max(1, math.ceil(len(entity_names) / 10))
    return DBSCAN(eps=0.5, min_samples=min_samples).fit_predict(eigvecs_selected).tolist()


def _classify_by_nearest_neighbor(input_embeddings, reference_embeddings, labels, n_neighbors=1):
    input_embeddings     = _sanitize_embeddings(input_embeddings)
    reference_embeddings = _sanitize_embeddings(reference_embeddings)
    sims = np.clip(np.dot(input_embeddings, reference_embeddings.T), -1.0, 1.0)
    result_labels = []
    for i in range(len(input_embeddings)):
        top_indices = np.argsort(sims[i])[-n_neighbors:][::-1]
        result_labels.append(labels[top_indices[0]])
    return result_labels

# ============================================================================
# Entity alignment
# ============================================================================

def _prepare_and_cluster_entities(nearby_text_entities, nearby_relationships):
    if not nearby_text_entities:
        return np.array([]), []
    descriptions = [e["description"] for e in nearby_text_entities]
    entity_names = [e["entity_name"] for e in nearby_text_entities]
    embeddings = _sanitize_embeddings(np.array(get_embed_model().encode(descriptions)))
    labels = _compute_spectral_labels(embeddings, entity_names, nearby_relationships)
    return embeddings, labels


def align_single_image_entity(img_entity_name, text_chunks, working_dir: str | None = None):
    image_data  = get_image_data(working_dir)
    entity_info = image_data.get(img_entity_name, {})
    image_path  = entity_info.get("image_path")
    description = entity_info.get("description", "")
    chunk_index = entity_info.get("chunk_order_index", 0)
    nearby_chunks = get_nearby_chunks(text_chunks, chunk_index)
    entity_types  = [t.upper() for t in PROMPTS["DEFAULT_ENTITY_TYPES"]]
    with open(image_path, "rb") as f:
        img_base = base64.b64encode(f.read()).decode("utf-8")
    prompt = PROMPTS["image_entity_alignment_user"].format(
        entity_type=entity_types, img_entity=img_entity_name,
        img_entity_description=description, chunk_text=nearby_chunks
    )
    return normalize_to_json(get_mmllm_response(prompt, PROMPTS["image_entity_alignment_system"], img_base))


def get_possible_entities_image_clustering(image_entity_description, nearby_text_entities, nearby_relationships):
    if not nearby_text_entities:
        return []
    embeddings, labels = _prepare_and_cluster_entities(nearby_text_entities, nearby_relationships)
    if embeddings.size == 0:
        return []
    input_embedding = get_embed_model().encode([image_entity_description])
    target_label = _classify_by_nearest_neighbor(input_embedding, embeddings, labels, n_neighbors=3)[0]
    return [e for e, label in zip(nearby_text_entities, labels, strict=False) if label == target_label]


def get_possible_entities_text_clustering(filtered_image_entities, nearby_text_entities, nearby_relationships):
    if not nearby_text_entities:
        return [], []
    embeddings, labels = _prepare_and_cluster_entities(nearby_text_entities, nearby_relationships)
    if embeddings.size == 0:
        return [], []
    image_entity_with_labels = []
    if filtered_image_entities:
        img_embeddings = get_embed_model().encode([e["description"] for e in filtered_image_entities])
        img_labels     = _classify_by_nearest_neighbor(img_embeddings, embeddings, labels)
        for entity, label in zip(filtered_image_entities, img_labels, strict=False):
            image_entity_with_labels.append({
                "entity_name": entity["entity_name"], "label": label,
                "description": entity["description"], "entity_type": entity.get("entity_type", "image")
            })
    text_clustering_results = []
    for label in set(labels):
        cluster_entities = [
            {
                "entity_name": entity["entity_name"],
                "entity_type": entity["entity_type"],
                "description": entity["description"],
            }
            for entity, cluster_label in zip(nearby_text_entities, labels, strict=False)
            if cluster_label == label
        ]
        text_clustering_results.append({"label": label, "entities": cluster_entities})
    return image_entity_with_labels, text_clustering_results


def judge_image_entity_alignment(image_entity_name, image_entity_description, possible_entities, nearby_chunks):
    prompt = PROMPTS["image_entity_judgement_user"].format(
        img_entity=image_entity_name, img_entity_description=image_entity_description,
        possible_matched_entities=possible_entities, chunk_text=nearby_chunks
    )
    return get_llm_response(prompt, PROMPTS["image_entity_judgement_system"])

def judge_text_entity_alignment_clustering(image_entity_with_labels, text_clustering_results):
    clusters_info = [
        {"label": c["label"], "text_entities": [
            {"entity_name": e["entity_name"], "entity_type": e["entity_type"], "description": e["description"]}
            for e in c["entities"]
        ]}
        for c in text_clustering_results
    ]
    prompt_user = f"""
You are tasked with aligning image entities and text entities based on their labels and descriptions. Below are the clusters and the entities they contain.

Clusters information:
{{
    "clusters": [
        {", ".join([f'{{"label": {c["label"]}, "text_entities": {c["text_entities"]}}}' for c in clusters_info])}
    ]
}}

Image entities with labels:
{[{"entity_name": e["entity_name"], "label": e["label"], "description": e["description"], "entity_type": e["entity_type"]} for e in image_entity_with_labels]}

Instruction:
1. For each image entity, look at the corresponding cluster (same label).
2. Compare the description and type of the image entity with the text entities in the same cluster.
3. Identify matching entities between the image entities and text entities within the same cluster (same label).
4. For each match, create a new unified entity by merging the descriptions and including the source entities under "source_image_entities" and "source_text_entities".
5. Output a JSON list where each item represents a merged entity with the following structure:
    {{
        "entity_name": "Newly merged entity name",
        "entity_type": "Type of the merged entity",
        "description": "Merged description of the entity",
        "source_image_entities": ["List of matched image entity names"],
        "source_text_entities": ["List of matched text entity names"]
    }}
Include only one JSON list as the output, strictly following the structure above.
"""
    prompt_system = """You are an AI assistant skilled in aligning entities based on semantic descriptions and cluster information. Use the provided instructions to merge entities accurately."""
    merged_entities = get_llm_response(cur_prompt=prompt_user, system_content=prompt_system)
    normalized      = normalize_to_json_list(merged_entities)
    return [i for i in normalized if i.get("source_image_entities") and i.get("source_text_entities")]

# ============================================================================
# Image entity operations
# ============================================================================

def extract_image_entities(img_entity_name, working_dir: str | None = None):
    base = working_dir or parameter.WORKING_DIR
    path = os.path.join(base, f"images/{img_entity_name}/graph_{img_entity_name}_entity_relation.graphml")
    if not os.path.exists(path):
        logger.warning(f"⚠️  GraphML file not found: {path}")
        return []
    tree = ET.parse(path)
    root = tree.getroot()
    ns   = {"graphml": "http://graphml.graphdrawing.org/xmlns"}
    entities = []
    for node in root.findall("graphml:graph/graphml:node", ns):
        entity_name = (node.get("id") or "").strip('"')
        entity_type = description = ""
        for data in node.findall("graphml:data", ns):
            key = data.get("key")
            text = (data.text or "").strip('"')
            if key == "d0":
                entity_type = text
            elif key == "d1":
                description = text
        entities.append({"entity_name": entity_name, "entity_type": entity_type, "description": description})
    return entities


def enhance_image_entities(image_entities, nearby_chunks):
    prompt = PROMPTS["enhance_image_entity_user"].format(
        enhanced_image_entity_list=image_entities, chunk_text=nearby_chunks
    )
    return normalize_to_json_list(get_llm_response(prompt, PROMPTS["enhance_image_entity_system"]))


def image_knowledge_graph_alignment(image_entity_name, working_dir: str | None = None):
    image_data  = get_image_data(working_dir)
    chunk_kg    = get_chunk_knowledge_graph(working_dir)
    chunk_index = image_data[image_entity_name].get("chunk_order_index", 0)
    image_entities  = extract_image_entities(image_entity_name, working_dir)
    filtered        = [e for e in image_entities if e["entity_type"] not in ["ORI_IMG", "IMG"]]
    nearby_entities = get_nearby_entities(chunk_kg, chunk_index)
    nearby_rels     = get_nearby_relationships(chunk_kg, chunk_index)
    img_with_labels, text_clusters = get_possible_entities_text_clustering(filtered, nearby_entities, nearby_rels)
    return judge_text_entity_alignment_clustering(img_with_labels, text_clusters)


def enhanced_image_knowledge_graph(aligned_entities, image_entity_name, working_dir: str | None = None):
    base         = working_dir or parameter.WORKING_DIR
    image_data   = get_image_data(working_dir)
    text_chunks  = get_text_chunks(working_dir)
    img_kg_path  = os.path.join(base, f"images/{image_entity_name}/graph_{image_entity_name}_entity_relation.graphml")
    enhanced_path = os.path.join(base, f"images/{image_entity_name}/enhanced_graph_{image_entity_name}_entity_relation.graphml")
    image_entities = extract_image_entities(image_entity_name, working_dir)
    filtered       = [e for e in image_entities if e["entity_type"] not in ["ORI_IMG", "IMG"]]
    chunk_index    = image_data[image_entity_name].get("chunk_order_index", 0)
    nearby_chunks  = get_nearby_chunks(text_chunks, chunk_index)
    aligned_image_names = [e.get("source_image_entities", [None])[0] for e in aligned_entities if e.get("source_image_entities")]
    to_enhance = [e for e in filtered if e["entity_name"] not in aligned_image_names]
    enhanced   = enhance_image_entities(to_enhance, nearby_chunks)
    G = nx.read_graphml(img_kg_path)
    for entity in enhanced:
        original_name = entity.get("original_name")
        if not original_name or "description" not in entity:
            continue
        new_name = ensure_quoted(entity["entity_name"])
        for node_id in list(G.nodes()):
            if node_id.strip('"') == original_name:
                G = nx.relabel_nodes(G, {node_id: new_name})
                G.nodes[new_name]["description"] = entity["description"]
                break
    nx.write_graphml(G, enhanced_path)
    return enhanced_path

def image_knowledge_graph_update(enhanced_path, image_entity_name, working_dir: str | None = None):
    base        = working_dir or parameter.WORKING_DIR
    image_data  = get_image_data(working_dir)
    text_chunks = get_text_chunks(working_dir)
    chunk_kg    = get_chunk_knowledge_graph(working_dir)
    new_path    = os.path.join(base, f"images/{image_entity_name}/new_graph_{image_entity_name}_entity_relation.graphml")

    image_entity    = align_single_image_entity(image_entity_name, text_chunks, working_dir)
    chunk_index     = image_data[image_entity_name].get("chunk_order_index", 0)
    nearby_chunks   = get_nearby_chunks(text_chunks, chunk_index)
    nearby_entities = get_nearby_entities(chunk_kg, chunk_index)
    nearby_rels     = get_nearby_relationships(chunk_kg, chunk_index)

    if not image_entity:
        return enhanced_path
    entity_name = image_entity.get("entity_name", "no_match")
    entity_desc = image_entity.get("description", "")
    if entity_name.lower().replace(" ", "") in ["no_match", "nomatch"]:
        return enhanced_path

    possible_matches = get_possible_entities_image_clustering(entity_desc, nearby_entities, nearby_rels)
    matched_name     = judge_image_entity_alignment(entity_name, entity_desc, possible_matches, nearby_chunks)
    if not matched_name or not matched_name.strip():
        logger.warning(f"⚠️  Could not match image entity: {entity_name}")
        return enhanced_path

    matched_normalized = matched_name.strip().replace(" ", "").replace("\\", "").lower()
    G = nx.read_graphml(enhanced_path)
    source_node = None
    for node, data in G.nodes(data=True):
        if data.get("entity_type", "") in ['"ORI_IMG"', '"UNKNOWN"', "ORI_IMG", "UNKNOWN"]:
            source_node = node
            break
    if source_node is None:
        logger.warning("ORI_IMG node not found")
        return enhanced_path

    edges = list(G.edges(data=True))
    if edges:
        source_id = edges[0][2].get("source_id", "")
        order     = edges[0][2].get("order", 1)
    else:
        source_id = G.nodes[source_node].get("source_id", "")
        order     = 1

    matched = False
    for entity in nearby_entities:
        ename = entity.get("entity_name", "")
        if ename.strip().replace(" ", "").replace("\\", "").lower() == matched_normalized:
            matched = True
            quoted_name = ensure_quoted(ename)
            G.add_node(quoted_name, entity_type=entity["entity_type"], description=entity["description"], source_id=source_id)
            G.add_edge(source_node, quoted_name, weight=10.0, description=f"{source_node} is the image of {ename}.", source_id=source_id, order=order)
            break

    if not matched:
        G.add_node(entity_name, entity_type="IMG_ENTITY", description=entity_desc, source_id=source_id)
        G.add_edge(source_node, entity_name, weight=10.0, description=f"{source_node} is the image of {entity_name}.", source_id=source_id, order=order)

    nx.write_graphml(G, new_path)
    return new_path


def merge_graphs(image_graph_path, text_graph_path, aligned_entities, image_entity_name, working_dir: str | None = None):
    base         = working_dir or parameter.WORKING_DIR
    merged_path  = os.path.join(base, f"graph_merged_{image_entity_name}.graphml")
    image_graph  = nx.read_graphml(image_graph_path)
    text_graph   = nx.read_graphml(text_graph_path)
    if image_graph is None or text_graph is None:
        logger.error("❌ Failed to load graphs")
        return text_graph_path
    merged = nx.compose(image_graph, text_graph)
    for entity_info in aligned_entities:
        required_keys = ["entity_name", "entity_type", "description", "source_image_entities", "source_text_entities"]
        if not all(k in entity_info for k in required_keys):
            continue
        src_image = entity_info["source_image_entities"]
        src_text  = entity_info["source_text_entities"]
        if not src_image or not src_text:
            continue
        target = ensure_quoted(src_image[0])
        src_id_img = image_graph.nodes.get(target, {}).get("source_id", "")
        src_id_txt = text_graph.nodes.get(ensure_quoted(src_text[0]), {}).get("source_id", "")
        combined_source_id = GRAPH_FIELD_SEP.join(filter(None, [src_id_img, src_id_txt]))
        for candidate_entity in list(set(src_image + src_text)):
            normalized_entity = ensure_quoted(candidate_entity)
            if normalized_entity == target or normalized_entity not in merged.nodes:
                continue
            for neighbor in list(merged.neighbors(normalized_entity)):
                if not merged.has_edge(target, neighbor):
                    merged.add_edge(target, neighbor)
                edge_data = merged.get_edge_data(normalized_entity, neighbor)
                target_edge_data = merged.get_edge_data(target, neighbor)
                if target_edge_data:
                    for key in edge_data:
                        if key in ["weight", "description", "source_id", "order"]:
                            target_edge_data[key] = edge_data.get(key, target_edge_data.get(key))
                else:
                    merged[target][neighbor].update(edge_data)
            merged.remove_node(normalized_entity)
        if target not in merged.nodes:
            merged.add_node(target)
        merged.nodes[target].update({"entity_type": entity_info["entity_type"], "description": entity_info["description"], "source_id": combined_source_id})
        new_name = ensure_quoted(entity_info["entity_name"])
        if new_name != target:
            merged = nx.relabel_nodes(merged, {target: new_name})
    nx.write_graphml(merged, merged_path)
    logger.info(f"🔗 Graph fusion complete: {merged_path}")
    return merged_path


# ============================================================================
# Entry point
# ============================================================================

async def fusion(img_ids: list[str], working_dir: str | None = None) -> str:
    """Run cross-modal graph fusion for all image entity IDs.

    Parameters
    ----------
    img_ids:
        List of image entity names to fuse into the text graph.
    working_dir:
        Workspace-scoped working directory. Defaults to global WORKING_DIR
        if not supplied (legacy / CLI usage).
    """
    base       = working_dir or parameter.WORKING_DIR
    graph_path = os.path.join(base, "graph_chunk_entity_relation.graphml")
    if not img_ids:
        return graph_path
    for image_name in tqdm(img_ids, desc="🔗 Graph fusion", unit="image"):
        merged_path = os.path.join(base, f"graph_merged_{image_name}.graphml")
        if os.path.exists(merged_path):
            graph_path = merged_path
            continue
        aligned       = image_knowledge_graph_alignment(image_name, working_dir)
        enhanced_path = enhanced_image_knowledge_graph(aligned, image_name, working_dir)
        updated_path  = image_knowledge_graph_update(enhanced_path, image_name, working_dir)
        graph_path    = merge_graphs(updated_path, graph_path, aligned, image_name, working_dir)
    return graph_path
