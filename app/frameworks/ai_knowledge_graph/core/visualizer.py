"""知识图谱可视化器
基于AI知识图谱框架的可视化功能，生成交互式HTML图谱
"""

from typing import List, Dict, Any, Optional
import logging
import networkx as nx
from pyvis.network import Network
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeGraphVisualizer:
    """知识图谱可视化器类"""
    
    def __init__(self, config):
        """初始化可视化器
        
        Args:
            config: 配置对象
        """
        self.config = config
        
        logger.info("知识图谱可视化器初始化完成")
    
    def visualize_knowledge_graph(
        self, 
        triples: List[Dict[str, Any]], 
        output_path: Optional[str] = None,
        visualization_type: str = "enhanced"
    ) -> Dict[str, Any]:
        """可视化知识图谱
        
        Args:
            triples: 三元组列表
            output_path: 输出路径，如果为None则生成临时文件
            visualization_type: 可视化类型，"enhanced"使用增强版HTML，"basic"使用基础Pyvis
            
        Returns:
            包含可视化结果的字典
        """
        if not triples:
            logger.warning("没有三元组数据用于可视化")
            return {
                "success": False,
                "error": "没有三元组数据",
                "statistics": {}
            }
        
        try:
            logger.info(f"开始可视化 {len(triples)} 个三元组，类型: {visualization_type}")
            
            if visualization_type == "enhanced":
                # 使用增强版HTML生成
                return self._generate_enhanced_visualization(triples, output_path)
            else:
                # 使用基础Pyvis生成
                return self._generate_basic_visualization(triples, output_path)
            
        except Exception as e:
            logger.error(f"可视化失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "statistics": {}
            }
    
    def _generate_enhanced_visualization(
        self, 
        triples: List[Dict[str, Any]], 
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成增强版可视化
        
        Args:
            triples: 三元组列表
            output_path: 输出路径
            
        Returns:
            可视化结果字典
        """
        # 生成增强版HTML
        html_content = self._generate_enhanced_html(triples)
        
        # 计算统计信息
        statistics = self._calculate_triples_statistics(triples)
        
        # 如果指定了输出路径，保存文件
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"增强版可视化保存至: {output_path}")
            except Exception as e:
                logger.warning(f"保存HTML文件失败: {str(e)}")
        
        # 构建图用于返回图数据
        graph = self._build_graph(triples)
        communities = self._detect_communities(graph)
        
        return {
            "success": True,
            "output_path": output_path,
            "html_content": html_content,
            "statistics": statistics,
            "visualization_type": "enhanced",
            "graph_data": {
                "nodes": list(graph.nodes()),
                "edges": list(graph.edges()),
                "communities": [list(community) for community in communities]
            }
        }
    
    def _generate_basic_visualization(
        self, 
        triples: List[Dict[str, Any]], 
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成基础Pyvis可视化
        
        Args:
            triples: 三元组列表
            output_path: 输出路径
            
        Returns:
            可视化结果字典
        """
        # 1. 构建图谱
        graph = self._build_graph(triples)
        
        # 2. 计算中心性指标
        centrality_metrics = self._calculate_centrality_metrics(graph)
        
        # 3. 检测社区
        communities = self._detect_communities(graph)
        
        # 4. 计算节点大小
        node_sizes = self._calculate_node_sizes(graph, centrality_metrics)
        
        # 5. 创建可视化网络
        vis_network = self._create_visualization_network()
        
        # 6. 添加节点和边
        self._add_nodes_and_edges_to_network(
            vis_network, graph, communities, node_sizes, triples
        )
        
        # 7. 配置可视化选项
        self._configure_visualization_options(vis_network)
        
        # 8. 生成输出路径
        if output_path is None:
            output_path = self._generate_output_path()
        
        # 9. 保存HTML文件
        vis_network.save_graph(output_path)
        
        # 10. 修改HTML以添加自定义样式
        self._customize_html_file(output_path)
        
        # 11. 计算统计信息
        statistics = self._calculate_statistics(graph, triples, communities)
        
        logger.info(f"基础可视化完成，保存至: {output_path}")
        
        # 读取HTML内容用于返回
        html_content = None
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            logger.warning(f"无法读取HTML内容: {str(e)}")

        return {
            "success": True,
            "output_path": output_path,
            "html_content": html_content,
            "statistics": statistics,
            "visualization_type": "basic",
            "graph_data": {
                "nodes": list(graph.nodes()),
                "edges": list(graph.edges()),
                "communities": [list(community) for community in communities]
            }
        }
    
    def _build_graph(self, triples: List[Dict[str, Any]]) -> nx.Graph:
        """构建networkx图
        
        Args:
            triples: 三元组列表
            
        Returns:
            构建的图
        """
        graph = nx.Graph()
        
        for triple in triples:
            subject = triple["subject"]
            obj = triple["object"]
            predicate = triple["predicate"]
            
            # 添加节点
            graph.add_node(subject)
            graph.add_node(obj)
            
            # 添加边，保留关系信息
            if graph.has_edge(subject, obj):
                # 如果边已存在，添加关系到现有边
                existing_relationships = graph[subject][obj].get("relationships", set())
                existing_relationships.add(predicate)
                graph[subject][obj]["relationships"] = existing_relationships
            else:
                graph.add_edge(subject, obj, relationships={predicate})
            
            # 保留三元组的其他属性
            edge_data = graph[subject][obj]
            if "inferred" in triple:
                edge_data["inferred"] = triple["inferred"]
            if "inference_type" in triple:
                edge_data["inference_type"] = triple["inference_type"]
        
        return graph
    
    def _calculate_centrality_metrics(self, graph: nx.Graph) -> Dict[str, Dict[str, float]]:
        """计算中心性指标
        
        Args:
            graph: networkx图
            
        Returns:
            中心性指标字典
        """
        metrics = {}
        
        if len(graph.nodes) == 0:
            return metrics
        
        try:
            # 度中心性
            metrics["degree"] = nx.degree_centrality(graph)
            
            # 介数中心性
            if len(graph.nodes) > 2:
                metrics["betweenness"] = nx.betweenness_centrality(graph)
            else:
                metrics["betweenness"] = {node: 0.0 for node in graph.nodes}
            
            # 特征向量中心性
            if len(graph.edges) > 0:
                try:
                    metrics["eigenvector"] = nx.eigenvector_centrality(graph, max_iter=1000)
                except:
                    # 如果计算失败，使用度中心性作为替代
                    metrics["eigenvector"] = metrics["degree"]
            else:
                metrics["eigenvector"] = {node: 0.0 for node in graph.nodes}
            
            # 接近中心性
            if nx.is_connected(graph):
                metrics["closeness"] = nx.closeness_centrality(graph)
            else:
                # 对于非连通图，分别计算每个连通组件的接近中心性
                metrics["closeness"] = {}
                for component in nx.connected_components(graph):
                    subgraph = graph.subgraph(component)
                    if len(subgraph) > 1:
                        closeness = nx.closeness_centrality(subgraph)
                        metrics["closeness"].update(closeness)
                    else:
                        metrics["closeness"][list(component)[0]] = 0.0
            
        except Exception as e:
            logger.warning(f"计算中心性指标失败: {str(e)}")
            # 降级到基本度中心性
            metrics["degree"] = nx.degree_centrality(graph)
            metrics["betweenness"] = {node: 0.0 for node in graph.nodes}
            metrics["eigenvector"] = metrics["degree"]
            metrics["closeness"] = {node: 0.0 for node in graph.nodes}
        
        return metrics
    
    def _detect_communities(self, graph: nx.Graph) -> List[set]:
        """检测社区
        
        Args:
            graph: networkx图
            
        Returns:
            社区列表
        """
        if len(graph.nodes) < 2:
            return [set(graph.nodes)]
        
        try:
            # 使用Louvain算法进行社区检测
            communities = nx.community.louvain_communities(graph)
            return [community for community in communities if len(community) >= 1]
        except Exception as e:
            logger.warning(f"社区检测失败: {str(e)}")
            # 降级到连接组件
            return [component for component in nx.connected_components(graph)]
    
    def _calculate_node_sizes(
        self, 
        graph: nx.Graph, 
        centrality_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, int]:
        """计算节点大小
        
        Args:
            graph: networkx图
            centrality_metrics: 中心性指标
            
        Returns:
            节点大小字典
        """
        node_sizes = {}
        
        if not centrality_metrics:
            # 如果没有中心性指标，使用度数
            for node in graph.nodes:
                node_sizes[node] = max(10, min(50, graph.degree(node) * 5 + 10))
            return node_sizes
        
        # 组合多个中心性指标
        for node in graph.nodes:
            degree_score = centrality_metrics.get("degree", {}).get(node, 0)
            betweenness_score = centrality_metrics.get("betweenness", {}).get(node, 0)
            eigenvector_score = centrality_metrics.get("eigenvector", {}).get(node, 0)
            
            # 加权组合
            combined_score = (
                0.4 * degree_score + 
                0.3 * betweenness_score + 
                0.3 * eigenvector_score
            )
            
            # 映射到大小范围 (15-60)
            size = int(15 + combined_score * 45)
            node_sizes[node] = max(15, min(60, size))
        
        return node_sizes
    
    def _create_visualization_network(self) -> Network:
        """创建可视化网络
        
        Returns:
            PyVis网络对象
        """
        # 配置网络
        height = self.config.visualization.get("height", "800px")
        width = self.config.visualization.get("width", "100%")
        bgcolor = self.config.visualization.get("bgcolor", "#ffffff")
        font_color = self.config.visualization.get("font_color", "#000000")
        
        net = Network(
            height=height,
            width=width,
            bgcolor=bgcolor,
            font_color=font_color,
            directed=False,
            neighborhood_highlight=True,
            select_menu=True,
            filter_menu=True
        )
        
        return net
    
    def _add_nodes_and_edges_to_network(
        self,
        net: Network,
        graph: nx.Graph,
        communities: List[set],
        node_sizes: Dict[str, int],
        triples: List[Dict[str, Any]]
    ):
        """添加节点和边到可视化网络
        
        Args:
            net: PyVis网络对象
            graph: networkx图
            communities: 社区列表
            node_sizes: 节点大小字典
            triples: 三元组列表
        """
        # 为社区分配颜色
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
            "#F7DC6F", "#BB8FCE", "#85C1E9", "#F8C471", "#82E0AA",
            "#F1948A", "#AED6F1", "#A9DFBF", "#F9E79F", "#D7BDE2"
        ]
        
        # 创建节点到社区的映射
        node_to_community = {}
        for i, community in enumerate(communities):
            for node in community:
                node_to_community[node] = i % len(colors)
        
        # 添加节点
        for node in graph.nodes:
            size = node_sizes.get(node, 20)
            color = colors[node_to_community.get(node, 0)]
            
            # 创建悬停信息
            degree = graph.degree(node)
            title = f"实体: {node}\n度数: {degree}"
            
            net.add_node(
                node,
                label=node,
                size=size,
                color=color,
                title=title,
                font={"size": max(12, size // 3)}
            )
        
        # 添加边
        for source, target, data in graph.edges(data=True):
            relationships = data.get("relationships", set())
            is_inferred = data.get("inferred", False)
            
            # 创建边标签
            if len(relationships) == 1:
                label = list(relationships)[0]
            else:
                label = f"{len(relationships)} 关系"
            
            # 创建悬停信息
            title = f"关系: {', '.join(relationships)}"
            if is_inferred:
                inference_type = data.get("inference_type", "unknown")
                title += f"\n(推断: {inference_type})"
            
            # 边样式
            edge_style = {
                "label": label,
                "title": title,
                "width": 2,
                "font": {"size": 10}
            }
            
            if is_inferred:
                edge_style["dashes"] = True
                edge_style["color"] = {"color": "#FF6B6B", "opacity": 0.7}
            else:
                edge_style["color"] = {"color": "#2E86AB", "opacity": 0.8}
            
            net.add_edge(source, target, **edge_style)
    
    def _configure_visualization_options(self, net: Network):
        """配置可视化选项
        
        Args:
            net: PyVis网络对象
        """
        # 物理模拟选项
        physics_options = {
            "enabled": True,
            "stabilization": {"enabled": True, "iterations": 100},
            "barnesHut": {
                "gravitationalConstant": -2000,
                "centralGravity": 0.3,
                "springLength": 200,
                "springConstant": 0.05,
                "damping": 0.09
            }
        }
        
        # 交互选项
        interaction_options = {
            "dragNodes": True,
            "dragView": True,
            "zoomView": True,
            "selectConnectedEdges": True,
            "hover": True,
            "navigationButtons": True,
            "keyboard": True
        }
        
        # 应用配置
        net.set_options({
            "physics": physics_options,
            "interaction": interaction_options,
            "edges": {
                "smooth": {"type": "continuous"},
                "arrows": {"to": {"enabled": False}}
            },
            "nodes": {
                "borderWidth": 2,
                "borderWidthSelected": 4,
                "chosen": True
            },
            "layout": {
                "improvedLayout": True
            }
        })
    
    def _generate_output_path(self) -> str:
        """生成输出路径
        
        Returns:
            输出文件路径
        """
        # 在临时目录中生成文件
        temp_dir = tempfile.gettempdir()
        filename = f"knowledge_graph_{os.getpid()}.html"
        return os.path.join(temp_dir, filename)
    
    def _customize_html_file(self, output_path: str):
        """自定义HTML文件
        
        Args:
            output_path: HTML文件路径
        """
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 添加自定义CSS和JavaScript
            custom_styles = """
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }
                
                .header {
                    text-align: center;
                    color: white;
                    margin-bottom: 20px;
                }
                
                .graph-container {
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    overflow: hidden;
                }
                
                .controls {
                    background: #f8f9fa;
                    padding: 15px;
                    border-bottom: 1px solid #dee2e6;
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    align-items: center;
                }
                
                .control-group {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }
                
                .control-group label {
                    font-weight: 500;
                    color: #495057;
                }
                
                .control-group input, .control-group select {
                    padding: 5px 10px;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                    font-size: 14px;
                }
                
                .legend {
                    background: #f8f9fa;
                    padding: 15px;
                    border-top: 1px solid #dee2e6;
                    font-size: 14px;
                }
                
                .legend-item {
                    display: inline-flex;
                    align-items: center;
                    margin-right: 20px;
                    margin-bottom: 5px;
                }
                
                .legend-line {
                    width: 30px;
                    height: 2px;
                    margin-right: 8px;
                }
                
                .original-line {
                    background: #2E86AB;
                }
                
                .inferred-line {
                    background: #FF6B6B;
                    background-image: repeating-linear-gradient(45deg, transparent, transparent 3px, white 3px, white 6px);
                }
            </style>
            """
            
            # 添加控制面板和图例
            controls_html = """
            <div class="header">
                <h1>知识图谱可视化</h1>
                <p>交互式知识图谱 - 拖拽节点，缩放查看，悬停显示详情</p>
            </div>
            
            <div class="graph-container">
                <div class="controls">
                    <div class="control-group">
                        <label>物理模拟:</label>
                        <input type="checkbox" id="physics-toggle" checked onchange="togglePhysics()">
                    </div>
                    <div class="control-group">
                        <label>节点标签:</label>
                        <input type="checkbox" id="labels-toggle" checked onchange="toggleLabels()">
                    </div>
                    <div class="control-group">
                        <label>边标签:</label>
                        <input type="checkbox" id="edge-labels-toggle" checked onchange="toggleEdgeLabels()">
                    </div>
                    <div class="control-group">
                        <label>主题:</label>
                        <select id="theme-select" onchange="changeTheme()">
                            <option value="light">浅色</option>
                            <option value="dark">深色</option>
                        </select>
                    </div>
                </div>
            """
            
            legend_html = """
                <div class="legend">
                    <strong>图例:</strong>
                    <div class="legend-item">
                        <div class="legend-line original-line"></div>
                        <span>原始关系</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-line inferred-line"></div>
                        <span>推断关系</span>
                    </div>
                    <div class="legend-item">
                        <span style="margin-left: 20px;"><strong>节点大小:</strong> 重要性指标</span>
                    </div>
                    <div class="legend-item">
                        <span style="margin-left: 20px;"><strong>节点颜色:</strong> 社区分组</span>
                    </div>
                </div>
            </div>
            """
            
            # 添加JavaScript控制函数
            custom_js = """
            <script>
                function togglePhysics() {
                    const enabled = document.getElementById('physics-toggle').checked;
                    network.setOptions({physics: {enabled: enabled}});
                }
                
                function toggleLabels() {
                    const show = document.getElementById('labels-toggle').checked;
                    const update = {nodes: {font: {size: show ? 14 : 0}}};
                    network.setOptions(update);
                }
                
                function toggleEdgeLabels() {
                    const show = document.getElementById('edge-labels-toggle').checked;
                    const update = {edges: {font: {size: show ? 10 : 0}}};
                    network.setOptions(update);
                }
                
                function changeTheme() {
                    const theme = document.getElementById('theme-select').value;
                    if (theme === 'dark') {
                        network.setOptions({
                            configure: {
                                container: document.getElementById('mynetworkid')
                            },
                            interaction: {hover: true},
                            physics: {enabled: true},
                            nodes: {
                                font: {color: '#ffffff'}
                            },
                            edges: {
                                font: {color: '#ffffff'}
                            }
                        });
                        document.body.style.background = 'linear-gradient(135deg, #2c3e50 0%, #34495e 100%)';
                        document.querySelector('.graph-container').style.background = '#2c3e50';
                    } else {
                        network.setOptions({
                            nodes: {
                                font: {color: '#000000'}
                            },
                            edges: {
                                font: {color: '#000000'}
                            }
                        });
                        document.body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                        document.querySelector('.graph-container').style.background = 'white';
                    }
                }
            </script>
            """
            
            # 插入自定义内容
            content = content.replace('<head>', f'<head>{custom_styles}')
            content = content.replace('<body>', f'<body>{controls_html}')
            content = content.replace('</body>', f'{legend_html}{custom_js}</body>')
            
            # 修改网络容器的样式
            content = content.replace(
                'style="width: 100%; height: 800px;',
                'style="width: 100%; height: 800px; border: none;'
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            logger.warning(f"自定义HTML文件失败: {str(e)}")
    
    def _calculate_statistics(
        self, 
        graph: nx.Graph, 
        triples: List[Dict[str, Any]], 
        communities: List[set]
    ) -> Dict[str, Any]:
        """计算图谱统计信息
        
        Args:
            graph: networkx图
            triples: 三元组列表
            communities: 社区列表
            
        Returns:
            统计信息字典
        """
        # 计算原始和推断的关系数量
        original_edges = sum(1 for triple in triples if not triple.get("inferred", False))
        inferred_edges = sum(1 for triple in triples if triple.get("inferred", False))
        
        # 计算连通性
        if len(graph.nodes) > 0:
            is_connected = nx.is_connected(graph)
            components = list(nx.connected_components(graph))
            largest_component_size = max(len(comp) for comp in components) if components else 0
        else:
            is_connected = False
            components = []
            largest_component_size = 0
        
        # 计算密度
        density = nx.density(graph) if len(graph.nodes) > 1 else 0
        
        # 计算平均聚类系数
        try:
            avg_clustering = nx.average_clustering(graph)
        except:
            avg_clustering = 0
        
        return {
            "nodes": len(graph.nodes),
            "edges": len(graph.edges),
            "triples": len(triples),
            "original_edges": original_edges,
            "inferred_edges": inferred_edges,
            "communities": len(communities),
            "is_connected": is_connected,
            "connected_components": len(components),
            "largest_component_size": largest_component_size,
            "density": round(density, 4),
            "average_clustering": round(avg_clustering, 4)
        }
    
    def _generate_enhanced_html(self, triples: List[Dict[str, Any]]) -> str:
        """生成增强的交互式HTML可视化（框架内置）
        
        Args:
            triples: 三元组列表
            
        Returns:
            HTML内容字符串
        """
        # 计算统计信息
        stats = self._calculate_triples_statistics(triples)
        
        # 生成可视化数据
        vis_data = self._prepare_visualization_data(triples)
        
        html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知识图谱可视化 - {title}</title>
    <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.7/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            padding: 30px;
            text-align: center;
            color: white;
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        
        .header p {{
            margin: 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        
        .main-content {{
            display: flex;
            height: 800px;
        }}
        
        .sidebar {{
            width: 300px;
            background: #f8f9fa;
            padding: 25px;
            border-right: 1px solid #e9ecef;
            overflow-y: auto;
        }}
        
        .visualization {{
            flex: 1;
            position: relative;
            background: white;
        }}
        
        #network {{
            width: 100%;
            height: 100%;
        }}
        
        .stats-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .stats-card h3 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 1.2em;
            display: flex;
            align-items: center;
        }}
        
        .stats-card h3:before {{
            content: "📊";
            margin-right: 8px;
        }}
        
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .stat-item:last-child {{
            border-bottom: none;
        }}
        
        .stat-label {{
            color: #666;
            font-weight: 500;
        }}
        
        .stat-value {{
            color: #333;
            font-weight: bold;
        }}
        
        .controls {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .controls h3 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 1.2em;
        }}
        
        .control-group {{
            margin-bottom: 15px;
        }}
        
        .control-group label {{
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }}
        
        .control-group input[type="range"] {{
            width: 100%;
            margin-bottom: 5px;
        }}
        
        .control-group button {{
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }}
        
        .control-group button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
        
        .legend {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .legend h3 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 1.2em;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
            border: 2px solid #ddd;
        }}
        
        .legend-text {{
            color: #555;
            font-size: 14px;
        }}
        
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #666;
        }}
        
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .info-panel {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            max-width: 300px;
            display: none;
        }}
        
        .info-panel h4 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        
        .info-panel p {{
            margin: 5px 0;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕸️ 知识图谱可视化</h1>
            <p>交互式图谱探索 - 包含 {node_count} 个实体，{edge_count} 个关系</p>
        </div>
        
        <div class="main-content">
            <div class="sidebar">
                <div class="stats-card">
                    <h3>图谱统计</h3>
                    <div class="stat-item">
                        <span class="stat-label">实体数量</span>
                        <span class="stat-value">{node_count}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">关系数量</span>
                        <span class="stat-value">{edge_count}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">原始关系</span>
                        <span class="stat-value">{original_count}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">推理关系</span>
                        <span class="stat-value">{inferred_count}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">关系密度</span>
                        <span class="stat-value">{density:.3f}</span>
                    </div>
                </div>
                
                <div class="controls">
                    <h3>🎛️ 控制面板</h3>
                    
                    <div class="control-group">
                        <label>节点大小</label>
                        <input type="range" id="nodeSize" min="10" max="50" value="25" 
                               oninput="updateNodeSize(this.value)">
                        <small>当前: <span id="nodeSizeValue">25</span></small>
                    </div>
                    
                    <div class="control-group">
                        <label>边长度</label>
                        <input type="range" id="edgeLength" min="100" max="400" value="200" 
                               oninput="updateEdgeLength(this.value)">
                        <small>当前: <span id="edgeLengthValue">200</span></small>
                    </div>
                    
                    <div class="control-group">
                        <button onclick="fitNetwork()">🔍 适应视图</button>
                    </div>
                    
                    <div class="control-group">
                        <button onclick="togglePhysics()">⚡ 切换物理模拟</button>
                    </div>
                    
                    <div class="control-group">
                        <button onclick="resetLayout()">🔄 重置布局</button>
                    </div>
                </div>
                
                <div class="legend">
                    <h3>🏷️ 图例说明</h3>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #4285F4;"></div>
                        <span class="legend-text">原始关系</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #EA4335;"></div>
                        <span class="legend-text">推理关系</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #34A853;"></div>
                        <span class="legend-text">高度数节点</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #FBBC05;"></div>
                        <span class="legend-text">普通节点</span>
                    </div>
                </div>
            </div>
            
            <div class="visualization">
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>正在加载知识图谱...</p>
                </div>
                <div id="network"></div>
                
                <div class="info-panel" id="infoPanel">
                    <h4 id="infoTitle">节点信息</h4>
                    <p id="infoContent">点击节点或边查看详细信息</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 图谱数据
        const graphData = {graph_data_json};
        
        // 网络配置
        let physicsEnabled = true;
        let network = null;
        
        // 初始化网络
        function initNetwork() {{
            const container = document.getElementById('network');
            
            const options = {{
                nodes: {{
                    shape: 'dot',
                    size: 25,
                    font: {{
                        size: 14,
                        color: '#333333'
                    }},
                    borderWidth: 2,
                    shadow: true
                }},
                edges: {{
                    width: 2,
                    color: {{inherit: 'from'}},
                    smooth: {{
                        type: 'continuous',
                        roundness: 0.5
                    }},
                    arrows: {{
                        to: {{enabled: true, scaleFactor: 0.8}}
                    }},
                    font: {{
                        size: 12,
                        align: 'middle'
                    }},
                    shadow: true
                }},
                physics: {{
                    enabled: physicsEnabled,
                    stabilization: {{iterations: 150}},
                    barnesHut: {{
                        gravitationalConstant: -2000,
                        centralGravity: 0.3,
                        springLength: 200,
                        springConstant: 0.05,
                        damping: 0.09,
                        avoidOverlap: 0.1
                    }}
                }},
                interaction: {{
                    hover: true,
                    selectConnectedEdges: false,
                    tooltipDelay: 200
                }},
                layout: {{
                    improvedLayout: true,
                    clusterThreshold: 150
                }}
            }};
            
            network = new vis.Network(container, graphData, options);
            
            // 网络稳定后隐藏加载动画
            network.on('stabilizationIterationsDone', function() {{
                document.getElementById('loading').style.display = 'none';
            }});
            
            // 点击事件
            network.on('click', function(params) {{
                showInfo(params);
            }});
            
            // 悬停事件
            network.on('hoverNode', function(params) {{
                highlightConnected(params.node);
            }});
            
            network.on('blurNode', function(params) {{
                clearHighlight();
            }});
        }}
        
        // 显示节点/边信息
        function showInfo(params) {{
            const infoPanel = document.getElementById('infoPanel');
            const infoTitle = document.getElementById('infoTitle');
            const infoContent = document.getElementById('infoContent');
            
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const nodeData = graphData.nodes.find(n => n.id === nodeId);
                infoTitle.textContent = `实体: ${{nodeData.label}}`;
                
                // 获取连接的边
                const connectedEdges = graphData.edges.filter(e => 
                    e.from === nodeId || e.to === nodeId);
                infoContent.innerHTML = `
                    <strong>连接数:</strong> ${{connectedEdges.length}}<br>
                    <strong>节点ID:</strong> ${{nodeId}}<br>
                    <strong>类型:</strong> ${{nodeData.group || '未知'}}
                `;
            }} else if (params.edges.length > 0) {{
                const edgeId = params.edges[0];
                const edgeData = graphData.edges.find(e => e.id === edgeId);
                infoTitle.textContent = `关系: ${{edgeData.label}}`;
                infoContent.innerHTML = `
                    <strong>从:</strong> ${{edgeData.from}}<br>
                    <strong>到:</strong> ${{edgeData.to}}<br>
                    <strong>类型:</strong> ${{edgeData.dashes ? '推理关系' : '原始关系'}}
                `;
            }}
            
            infoPanel.style.display = 'block';
        }}
        
        // 高亮连接的节点
        function highlightConnected(nodeId) {{
            // 简化的高亮实现
            console.log(`高亮节点: ${{nodeId}}`);
        }}
        
        // 清除高亮
        function clearHighlight() {{
            // 简化的清除高亮实现
            console.log('清除高亮');
        }}
        
        // 控制函数
        function updateNodeSize(value) {{
            document.getElementById('nodeSizeValue').textContent = value;
            const options = {{
                nodes: {{
                    size: parseInt(value)
                }}
            }};
            network.setOptions(options);
        }}
        
        function updateEdgeLength(value) {{
            document.getElementById('edgeLengthValue').textContent = value;
            const options = {{
                physics: {{
                    barnesHut: {{
                        springLength: parseInt(value)
                    }}
                }}
            }};
            network.setOptions(options);
        }}
        
        function fitNetwork() {{
            network.fit({{
                animation: {{
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }}
            }});
        }}
        
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{
                physics: {{enabled: physicsEnabled}}
            }});
        }}
        
        function resetLayout() {{
            initNetwork();
        }}
        
        // 初始化
        document.addEventListener('DOMContentLoaded', function() {{
            initNetwork();
        }});
    </script>
</body>
</html>'''
        
        return html_template.format(
            title="AI知识图谱",
            node_count=stats["nodes"],
            edge_count=stats["edges"], 
            original_count=stats["original_edges"],
            inferred_count=stats["inferred_edges"],
            density=stats["density"],
            graph_data_json=vis_data
        )
    
    def _prepare_visualization_data(self, triples: List[Dict[str, Any]]) -> str:
        """准备可视化数据
        
        Args:
            triples: 三元组列表
            
        Returns:
            JSON格式的可视化数据
        """
        import json
        
        # 收集所有节点
        nodes = set()
        for triple in triples:
            nodes.add(triple["subject"])
            nodes.add(triple["object"])
        
        # 计算节点度数
        node_degrees = {}
        for node in nodes:
            degree = sum(1 for t in triples 
                        if t["subject"] == node or t["object"] == node)
            node_degrees[node] = degree
        
        # 创建节点数据
        nodes_data = []
        for node in nodes:
            degree = node_degrees[node]
            # 根据度数设置颜色和大小
            if degree > 5:
                color = "#34A853"  # 绿色 - 高度数节点
                size = 30
            else:
                color = "#FBBC05"  # 黄色 - 普通节点
                size = 20
                
            nodes_data.append({
                "id": node,
                "label": node,
                "color": {"background": color, "border": "#333"},
                "size": size,
                "originalColor": {"background": color, "border": "#333"},
                "group": "entity"
            })
        
        # 创建边数据
        edges_data = []
        for i, triple in enumerate(triples):
            is_inferred = triple.get("inferred", False)
            color = "#EA4335" if is_inferred else "#4285F4"  # 红色推理，蓝色原始
            
            edges_data.append({
                "id": i,
                "from": triple["subject"],
                "to": triple["object"],
                "label": triple["predicate"],
                "color": color,
                "dashes": is_inferred,
                "width": 2 if is_inferred else 3
            })
        
        return json.dumps({
            "nodes": nodes_data,
            "edges": edges_data
        }, ensure_ascii=False, indent=2)
    
    def _calculate_triples_statistics(self, triples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算三元组统计信息
        
        Args:
            triples: 三元组列表
            
        Returns:
            统计信息字典
        """
        # 收集节点
        nodes = set()
        for triple in triples:
            nodes.add(triple["subject"])
            nodes.add(triple["object"])
        
        # 统计推理关系
        inferred_count = sum(1 for t in triples if t.get("inferred", False))
        original_count = len(triples) - inferred_count
        
        # 计算密度
        node_count = len(nodes)
        edge_count = len(triples)
        max_edges = node_count * (node_count - 1) if node_count > 1 else 1
        density = edge_count / max_edges if max_edges > 0 else 0
        
        return {
            "nodes": node_count,
            "edges": edge_count,
            "original_edges": original_count,
            "inferred_edges": inferred_count,
            "density": density,
            "max_possible_edges": max_edges
        } 