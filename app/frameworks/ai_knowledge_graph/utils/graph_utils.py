"""图工具模块
提供知识图谱的操作、分析和实用功能
"""

from typing import List, Dict, Any, Set, Tuple, Optional
import logging
import networkx as nx
from collections import defaultdict, Counter
import json

logger = logging.getLogger(__name__)


class GraphUtils:
    """图工具类，提供知识图谱的各种操作功能"""
    
    @staticmethod
    def build_networkx_graph(triples: List[Dict[str, Any]]) -> nx.Graph:
        """构建NetworkX图
        
        Args:
            triples: 三元组列表
            
        Returns:
            NetworkX图对象
        """
        graph = nx.Graph()
        
        for triple in triples:
            subject = triple.get("subject", "")
            obj = triple.get("object", "")
            predicate = triple.get("predicate", "")
            
            if subject and obj:  # 确保有效的主语和宾语
                # 添加边，保留关系信息
                if graph.has_edge(subject, obj):
                    # 如果边已存在，添加关系
                    edge_data = graph[subject][obj]
                    if "relationships" not in edge_data:
                        edge_data["relationships"] = set()
                    edge_data["relationships"].add(predicate)
                else:
                    graph.add_edge(subject, obj, relationships={predicate})
                
                # 添加三元组属性
                edge_data = graph[subject][obj]
                if triple.get("inferred", False):
                    edge_data["inferred"] = True
                    edge_data["inference_type"] = triple.get("inference_type", "unknown")
        
        return graph
    
    @staticmethod
    def find_shortest_path(
        triples: List[Dict[str, Any]], 
        source: str, 
        target: str
    ) -> Optional[List[str]]:
        """查找两个实体间的最短路径
        
        Args:
            triples: 三元组列表
            source: 源实体
            target: 目标实体
            
        Returns:
            最短路径列表或None
        """
        try:
            graph = GraphUtils.build_networkx_graph(triples)
            
            if source not in graph or target not in graph:
                return None
            
            path = nx.shortest_path(graph, source, target)
            return path
            
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        except Exception as e:
            logger.warning(f"查找最短路径失败: {str(e)}")
            return None
    
    @staticmethod
    def get_neighbors(
        triples: List[Dict[str, Any]], 
        entity: str, 
        max_distance: int = 1
    ) -> Set[str]:
        """获取实体的邻居
        
        Args:
            triples: 三元组列表
            entity: 实体名称
            max_distance: 最大距离
            
        Returns:
            邻居实体集合
        """
        try:
            graph = GraphUtils.build_networkx_graph(triples)
            
            if entity not in graph:
                return set()
            
            neighbors = set()
            
            # 使用BFS查找指定距离内的所有邻居
            visited = set()
            queue = [(entity, 0)]
            
            while queue:
                current, distance = queue.pop(0)
                
                if current in visited or distance > max_distance:
                    continue
                
                visited.add(current)
                
                if distance > 0:  # 不包括自己
                    neighbors.add(current)
                
                if distance < max_distance:
                    for neighbor in graph.neighbors(current):
                        if neighbor not in visited:
                            queue.append((neighbor, distance + 1))
            
            return neighbors
            
        except Exception as e:
            logger.warning(f"获取邻居失败: {str(e)}")
            return set()
    
    @staticmethod
    def calculate_graph_metrics(triples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算图谱指标
        
        Args:
            triples: 三元组列表
            
        Returns:
            图谱指标字典
        """
        try:
            graph = GraphUtils.build_networkx_graph(triples)
            
            metrics = {
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
                "density": nx.density(graph) if len(graph.nodes) > 1 else 0,
                "is_connected": nx.is_connected(graph),
                "connected_components": nx.number_connected_components(graph)
            }
            
            # 计算中心性指标
            if len(graph.nodes) > 0:
                degree_centrality = nx.degree_centrality(graph)
                metrics["max_degree_centrality"] = max(degree_centrality.values()) if degree_centrality else 0
                metrics["avg_degree"] = sum(dict(graph.degree()).values()) / len(graph.nodes)
                
                if len(graph.nodes) > 2:
                    betweenness = nx.betweenness_centrality(graph)
                    metrics["max_betweenness_centrality"] = max(betweenness.values()) if betweenness else 0
                else:
                    metrics["max_betweenness_centrality"] = 0
            
            # 计算聚类系数
            if len(graph.edges) > 0:
                clustering = nx.average_clustering(graph)
                metrics["average_clustering"] = clustering
            else:
                metrics["average_clustering"] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"计算图谱指标失败: {str(e)}")
            return {}
    
    @staticmethod
    def detect_communities(
        triples: List[Dict[str, Any]], 
        algorithm: str = "louvain"
    ) -> List[Set[str]]:
        """检测社区
        
        Args:
            triples: 三元组列表
            algorithm: 社区检测算法
            
        Returns:
            社区列表
        """
        try:
            graph = GraphUtils.build_networkx_graph(triples)
            
            if len(graph.nodes) < 2:
                return [set(graph.nodes)]
            
            if algorithm.lower() == "louvain":
                communities = nx.community.louvain_communities(graph)
            elif algorithm.lower() == "greedy":
                communities = nx.community.greedy_modularity_communities(graph)
            else:
                # 降级到连接组件
                communities = [set(comp) for comp in nx.connected_components(graph)]
            
            return [community for community in communities if len(community) >= 1]
            
        except Exception as e:
            logger.warning(f"社区检测失败: {str(e)}")
            return [set()]
    
    @staticmethod
    def get_important_entities(
        triples: List[Dict[str, Any]], 
        top_k: int = 10,
        metric: str = "degree"
    ) -> List[Tuple[str, float]]:
        """获取重要实体
        
        Args:
            triples: 三元组列表
            top_k: 返回数量
            metric: 重要性指标 (degree, betweenness, eigenvector)
            
        Returns:
            (实体, 分数)列表
        """
        try:
            graph = GraphUtils.build_networkx_graph(triples)
            
            if len(graph.nodes) == 0:
                return []
            
            if metric == "degree":
                centrality = nx.degree_centrality(graph)
            elif metric == "betweenness":
                centrality = nx.betweenness_centrality(graph)
            elif metric == "eigenvector":
                try:
                    centrality = nx.eigenvector_centrality(graph)
                except:
                    # 如果计算失败，降级到度中心性
                    centrality = nx.degree_centrality(graph)
            else:
                centrality = nx.degree_centrality(graph)
            
            # 排序并返回top_k
            sorted_entities = sorted(
                centrality.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return sorted_entities[:top_k]
            
        except Exception as e:
            logger.warning(f"获取重要实体失败: {str(e)}")
            return []
    
    @staticmethod
    def filter_triples_by_entities(
        triples: List[Dict[str, Any]], 
        entities: Set[str]
    ) -> List[Dict[str, Any]]:
        """根据实体过滤三元组
        
        Args:
            triples: 三元组列表
            entities: 实体集合
            
        Returns:
            过滤后的三元组列表
        """
        filtered = []
        
        for triple in triples:
            subject = triple.get("subject", "")
            obj = triple.get("object", "")
            
            if subject in entities or obj in entities:
                filtered.append(triple)
        
        return filtered
    
    @staticmethod
    def get_entity_relations(
        triples: List[Dict[str, Any]], 
        entity: str
    ) -> Dict[str, List[str]]:
        """获取实体的所有关系
        
        Args:
            triples: 三元组列表
            entity: 实体名称
            
        Returns:
            关系字典 {"outgoing": [...], "incoming": [...]}
        """
        relations = {
            "outgoing": [],  # 以该实体为主语的关系
            "incoming": []   # 以该实体为宾语的关系
        }
        
        for triple in triples:
            subject = triple.get("subject", "")
            obj = triple.get("object", "")
            predicate = triple.get("predicate", "")
            
            if subject == entity:
                relations["outgoing"].append({
                    "predicate": predicate,
                    "object": obj,
                    "inferred": triple.get("inferred", False)
                })
            elif obj == entity:
                relations["incoming"].append({
                    "predicate": predicate,
                    "subject": subject,
                    "inferred": triple.get("inferred", False)
                })
        
        return relations
    
    @staticmethod
    def merge_graphs(
        triples_list: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """合并多个知识图谱
        
        Args:
            triples_list: 多个三元组列表
            
        Returns:
            合并后的三元组列表
        """
        merged = []
        seen = set()
        
        for triples in triples_list:
            for triple in triples:
                # 创建唯一标识
                key = (
                    triple.get("subject", "").lower(),
                    triple.get("predicate", "").lower(),
                    triple.get("object", "").lower()
                )
                
                if key not in seen:
                    seen.add(key)
                    merged.append(triple)
        
        return merged
    
    @staticmethod
    def export_to_cypher(triples: List[Dict[str, Any]]) -> str:
        """导出为Cypher查询语句
        
        Args:
            triples: 三元组列表
            
        Returns:
            Cypher查询语句
        """
        cypher_statements = []
        
        # 创建节点
        entities = set()
        for triple in triples:
            entities.add(triple.get("subject", ""))
            entities.add(triple.get("object", ""))
        
        for entity in entities:
            if entity:  # 跳过空实体
                safe_entity = entity.replace("'", "\\'")
                cypher_statements.append(f"CREATE (:{safe_entity.replace(' ', '_')} {{name: '{safe_entity}'}})")
        
        # 创建关系
        for triple in triples:
            subject = triple.get("subject", "")
            obj = triple.get("object", "")
            predicate = triple.get("predicate", "").replace(" ", "_").upper()
            
            if subject and obj and predicate:
                safe_subject = subject.replace("'", "\\'")
                safe_object = obj.replace("'", "\\'")
                
                cypher_statements.append(
                    f"MATCH (a {{name: '{safe_subject}'}}), (b {{name: '{safe_object}'}}) "
                    f"CREATE (a)-[:{predicate}]->(b)"
                )
        
        return ";\n".join(cypher_statements) + ";"
    
    @staticmethod
    def calculate_similarity(
        triples1: List[Dict[str, Any]], 
        triples2: List[Dict[str, Any]]
    ) -> float:
        """计算两个知识图谱的相似度
        
        Args:
            triples1: 第一个三元组列表
            triples2: 第二个三元组列表
            
        Returns:
            相似度分数 (0-1)
        """
        try:
            # 提取实体集合
            entities1 = set()
            entities2 = set()
            
            for triple in triples1:
                entities1.add(triple.get("subject", ""))
                entities1.add(triple.get("object", ""))
            
            for triple in triples2:
                entities2.add(triple.get("subject", ""))
                entities2.add(triple.get("object", ""))
            
            # 计算Jaccard相似度
            intersection = len(entities1.intersection(entities2))
            union = len(entities1.union(entities2))
            
            if union == 0:
                return 0.0
            
            return intersection / union
            
        except Exception as e:
            logger.warning(f"计算相似度失败: {str(e)}")
            return 0.0 