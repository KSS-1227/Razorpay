"""
知识图谱可视化服务器

提供 GraphML 解析和 Web 可视化界面。
"""

import json
import os
import logging
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

logger = logging.getLogger(__name__)

# GraphML 解析缓存
_graphml_cache = {}


def parse_graphml(filepath: str) -> dict:
    """解析 GraphML 文件，返回节点和边数据"""
    if filepath in _graphml_cache:
        cache_time, data = _graphml_cache[filepath]
        if os.path.exists(filepath) and os.path.getmtime(filepath) <= cache_time:
            return data
    
    if not os.path.exists(filepath):
        return None
    
    nodes = []
    edges = []
    entity_types = {}
    
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}
        
        # 获取属性键映射
        key_map = {}
        for key in root.findall('graphml:key', ns):
            key_id = key.get('id')
            key_name = key.get('attr.name')
            key_map[key_id] = key_name
        
        graph = root.find('graphml:graph', ns)
        if graph is None:
            return None
        
        # 解析节点
        for node in graph.findall('graphml:node', ns):
            node_id = node.get('id', '').strip('"')
            node_data = {'id': node_id}
            
            for data in node.findall('graphml:data', ns):
                key_id = data.get('key')
                key_name = key_map.get(key_id, key_id)
                value = (data.text or '').strip('"')
                node_data[key_name] = value
            
            entity_type = node_data.get('entity_type', 'UNKNOWN').strip('"')
            node_data['entity_type'] = entity_type
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            nodes.append(node_data)
        
        # 解析边
        for edge in graph.findall('graphml:edge', ns):
            source = edge.get('source', '').strip('"')
            target = edge.get('target', '').strip('"')
            edge_data = {'source': source, 'target': target}
            
            for data in edge.findall('graphml:data', ns):
                key_id = data.get('key')
                key_name = key_map.get(key_id, key_id)
                value = (data.text or '').strip('"')
                edge_data[key_name] = value
            
            edges.append(edge_data)
        
        result = {
            'nodes': nodes,
            'edges': edges,
            'entity_types': entity_types,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }
        
        _graphml_cache[filepath] = (os.path.getmtime(filepath), result)
        return result
        
    except Exception as e:
        logger.error(f"解析 GraphML 失败: {e}")
        return None


def create_visualization_app(output_dir: str, working_dir: str, graph_path: str = None):
    """创建可视化 Flask 应用
    
    Args:
        output_dir: 输出目录
        working_dir: 工作目录
        graph_path: 明确指定的图谱文件路径（可选）
    """
    
    # 静态文件目录 (server.py 所在目录)
    static_dir = os.path.dirname(__file__)
    
    app = Flask(__name__, static_folder=static_dir)
    CORS(app)
    
    def find_graphml():
        """查找可用的 GraphML 文件"""
        # 1. 优先使用明确指定的路径
        if graph_path and os.path.exists(graph_path):
            return graph_path
        
        # 2. 搜索 output_dir 中的所有 .graphml 文件
        if os.path.exists(output_dir):
            graphml_files = [f for f in os.listdir(output_dir) if f.endswith('.graphml')]
            if graphml_files:
                # 优先选择 mmkg 相关的文件
                for name in graphml_files:
                    if 'mmkg' in name.lower():
                        return os.path.join(output_dir, name)
                # 否则返回第一个
                return os.path.join(output_dir, graphml_files[0])
        
        return None
    
    @app.route('/')
    def index():
        return send_from_directory(static_dir, 'graph_explorer.html')
    
    @app.route('/api/graph/info')
    def graph_info():
        """获取图谱基本信息"""
        graphml_path = find_graphml()
        if not graphml_path:
            return jsonify({'success': False, 'error': '未找到图谱文件'})
        
        data = parse_graphml(graphml_path)
        if not data:
            return jsonify({'success': False, 'error': '解析图谱失败'})
        
        return jsonify({
            'success': True,
            'path': graphml_path,
            'node_count': data['node_count'],
            'edge_count': data['edge_count'],
            'entity_types': data['entity_types'],
            'size': os.path.getsize(graphml_path)
        })
    
    @app.route('/api/graph/content')
    def graph_content():
        """获取图谱内容"""
        graphml_path = find_graphml()
        if not graphml_path:
            return jsonify({'success': False, 'error': '未找到图谱文件'})
        
        data = parse_graphml(graphml_path)
        if not data:
            return jsonify({'success': False, 'error': '解析图谱失败'})
        
        limit = int(request.args.get('limit', 2000))
        nodes = data['nodes'][:limit]
        
        # 筛选相关边
        node_ids = {n['id'] for n in nodes}
        edges = [e for e in data['edges'] if e['source'] in node_ids and e['target'] in node_ids]
        
        return jsonify({
            'success': True,
            'nodes': nodes,
            'edges': edges,
            'entity_types': data['entity_types'],
            'total_nodes': data['node_count'],
            'total_edges': data['edge_count'],
            'has_more': len(data['nodes']) > limit
        })
    
    @app.route('/api/graph/search')
    def graph_search():
        """搜索节点"""
        query = request.args.get('q', '').lower().strip()
        if not query:
            return jsonify({'success': True, 'results': []})
        
        graphml_path = find_graphml()
        if not graphml_path:
            return jsonify({'success': False, 'error': '未找到图谱文件'})
        
        data = parse_graphml(graphml_path)
        if not data:
            return jsonify({'success': False, 'error': '解析图谱失败'})
        
        results = []
        for node in data['nodes']:
            node_id = node.get('id', '')
            node_id_lower = node_id.lower()
            desc = node.get('description', '').lower()
            
            # 计算匹配分数 (分数越低排名越前)
            score = None
            if node_id_lower == query:
                score = 0  # 精确匹配
            elif node_id_lower.startswith(query):
                score = 1 + len(node_id) * 0.001  # 前缀匹配，短名称优先
            elif query in node_id_lower:
                score = 2 + len(node_id) * 0.001  # 包含匹配，短名称优先
            elif query in desc:
                score = 3 + len(node_id) * 0.001  # 描述匹配
            
            if score is not None:
                results.append({
                    'id': node['id'],
                    'entity_type': node.get('entity_type', 'UNKNOWN'),
                    'description': node.get('description', '')[:200],
                    '_score': score
                })
        
        # 按分数排序并限制数量
        results.sort(key=lambda x: x['_score'])
        results = results[:50]
        
        # 移除内部字段
        for r in results:
            del r['_score']
        
        return jsonify({'success': True, 'results': results})
    
    @app.route('/api/graph/retrieve')
    def graph_retrieve():
        """检索相关节点和边（用于子图高亮）"""
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'success': False, 'error': '请输入检索问题'})
        
        graphml_path = find_graphml()
        if not graphml_path:
            return jsonify({'success': False, 'error': '未找到图谱文件'})
        
        try:
            # 导入检索模块
            from src.retrieval.query import (
                read_graphml, load_or_build_embeddings, find_similar_nodes
            )
            from src.parameter import RETRIEVAL_THRESHOLD
            
            # 加载图谱和embeddings
            graph = read_graphml(graphml_path)
            embeddings = load_or_build_embeddings(graph, graphml_path)
            
            # 查找相似节点
            similar_nodes = find_similar_nodes(query, embeddings, RETRIEVAL_THRESHOLD, top_k=20)
            
            if not similar_nodes:
                return jsonify({
                    'success': True, 
                    'nodes': [], 
                    'edges': [],
                    'message': '未找到相关节点'
                })
            
            # 获取节点名称集合（去除引号以匹配可视化中的格式）
            node_names_raw = {n['entity_name'] for n in similar_nodes}
            node_names_clean = {name.strip('"') for name in node_names_raw}
            
            # 获取相关边
            related_edges = []
            for node_name in node_names_raw:
                if graph.has_node(node_name):
                    for u, v in graph.edges(node_name):
                        # 只保留两端都在结果中的边
                        if u in node_names_raw and v in node_names_raw:
                            related_edges.append({
                                'source': u.strip('"'),
                                'target': v.strip('"')
                            })
            
            # 去重边
            seen = set()
            unique_edges = []
            for e in related_edges:
                key = tuple(sorted([e['source'], e['target']]))
                if key not in seen:
                    seen.add(key)
                    unique_edges.append(e)
            
            return jsonify({
                'success': True,
                'nodes': [name.strip('"') for name in node_names_raw],
                'edges': unique_edges,
                'scores': {n['entity_name'].strip('"'): n['score'] for n in similar_nodes}
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})
    
    return app


def run_visualization_server(output_dir: str, working_dir: str, port: int = 8080, graph_path: str = None):
    """运行可视化服务器"""
    app = create_visualization_app(output_dir, working_dir, graph_path)
    
    print(f"\n{'='*60}")
    print(f"🌐 知识图谱可视化服务器已启动")
    print(f"   访问地址: http://localhost:{port}")
    print(f"   输出目录: {output_dir}")
    if graph_path:
        print(f"   图谱文件: {graph_path}")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)
