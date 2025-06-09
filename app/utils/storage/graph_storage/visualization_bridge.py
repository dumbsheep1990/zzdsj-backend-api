"""
ArangoDB与NetworkX可视化系统桥接适配器
实现ArangoDB数据与现有HTML生成系统的无缝集成
"""

import asyncio
import logging
import tempfile
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

import networkx as nx

from .arangodb_adapter import ArangoDBAdapter
from .postgresql_age_adapter import PostgreSQLAGEAdapter

logger = logging.getLogger(__name__)

class GraphVisualizationBridge:
    """图数据库与可视化系统的桥接器"""
    
    def __init__(self, graph_db_adapter: Union[ArangoDBAdapter, PostgreSQLAGEAdapter]):
        """
        初始化桥接器
        
        Args:
            graph_db_adapter: 图数据库适配器实例
        """
        self.graph_db = graph_db_adapter
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def generate_html_visualization(
        self,
        tenant_id: str,
        graph_name: str,
        output_path: Optional[str] = None,
        visualization_type: str = "interactive",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        从ArangoDB数据生成HTML可视化
        
        Args:
            tenant_id: 租户ID
            graph_name: 图名称
            output_path: 输出文件路径（可选）
            visualization_type: 可视化类型 (simple/interactive/enhanced)
            config: 可视化配置
            
        Returns:
            生成结果字典
        """
        try:
            # 1. 从图数据库加载数据
            self.logger.info(f"从图数据库加载数据: {tenant_id}/{graph_name}")
            graph_data = await self.graph_db.load_knowledge_graph(tenant_id, graph_name)
            
            if not graph_data.get("success", False):
                raise Exception(f"数据加载失败: {graph_data.get('error', 'Unknown error')}")
            
            triples = graph_data.get("triples", [])
            if not triples:
                self.logger.warning("没有找到三元组数据")
                return {
                    "success": False,
                    "error": "没有可视化的数据",
                    "triples_count": 0
                }
            
            # 2. 转换为标准三元组格式
            standard_triples = self._convert_to_standard_format(triples)
            
            # 3. 根据类型选择可视化器
            visualizer = self._get_visualizer(visualization_type, config)
            
            # 4. 生成HTML可视化
            self.logger.info(f"使用{visualization_type}可视化器生成HTML...")
            result = await self._generate_visualization(
                visualizer, standard_triples, output_path, tenant_id, graph_name
            )
            
            return {
                "success": True,
                "html_path": result["html_path"],
                "html_content": result.get("html_content"),
                "statistics": result.get("statistics", {}),
                "triples_count": len(standard_triples),
                "visualization_type": visualization_type
            }
            
        except Exception as e:
            self.logger.error(f"HTML可视化生成失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "triples_count": 0
            }
    
    def _convert_to_standard_format(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将图数据库的三元组格式转换为可视化器标准格式
        
        Args:
            triples: 图数据库三元组
            
        Returns:
            标准格式三元组列表
        """
        standard_triples = []
        
        for triple in triples:
            # 处理不同数据库的格式差异
            if isinstance(triple, dict):
                # 标准格式检查
                if all(key in triple for key in ["subject", "predicate", "object"]):
                    standard_triple = {
                        "subject": str(triple["subject"]),
                        "predicate": str(triple["predicate"]), 
                        "object": str(triple["object"]),
                        "confidence": float(triple.get("confidence", 1.0)),
                        "inferred": bool(triple.get("inferred", False)),
                        "source": triple.get("source", "knowledge_graph"),
                        "metadata": triple.get("metadata", {})
                    }
                    standard_triples.append(standard_triple)
                else:
                    self.logger.warning(f"三元组格式不完整: {triple}")
            else:
                self.logger.warning(f"无效的三元组类型: {type(triple)}")
        
        self.logger.info(f"转换了 {len(standard_triples)} 个标准三元组")
        return standard_triples
    
    def _get_visualizer(self, visualization_type: str, config: Optional[Dict[str, Any]]):
        """
        根据类型获取可视化器
        
        Args:
            visualization_type: 可视化类型
            config: 配置
            
        Returns:
            可视化器实例
        """
        # 导入现有的可视化器
        if visualization_type == "simple":
            from simple_test import SimpleKnowledgeGraphProcessor
            return SimpleKnowledgeGraphProcessor()
            
        elif visualization_type == "interactive":
            from interactive_knowledge_graph import InteractiveKnowledgeGraphBuilder
            return InteractiveKnowledgeGraphBuilder()
            
        elif visualization_type == "enhanced":
            from enhanced_knowledge_graph_widget import EnhancedKnowledgeGraphWidget
            return EnhancedKnowledgeGraphWidget()
            
        else:
            # 默认使用PyVis实现
            return self._create_default_visualizer(config)
    
    def _create_default_visualizer(self, config: Optional[Dict[str, Any]]):
        """创建默认的PyVis可视化器"""
        class DefaultVisualizer:
            def __init__(self, config):
                self.config = config or {}
            
            def visualize_knowledge_graph(self, triples, output_path):
                from pyvis.network import Network
                
                net = Network(
                    height="800px", 
                    width="100%", 
                    bgcolor="#ffffff", 
                    font_color="black",
                    directed=True
                )
                
                # 添加节点和边
                nodes = set()
                for triple in triples:
                    nodes.add(triple['subject'])
                    nodes.add(triple['object'])
                
                for node in nodes:
                    net.add_node(node, label=node, size=20)
                
                for triple in triples:
                    is_inferred = triple.get('inferred', False)
                    color = '#ff0000' if is_inferred else '#0066cc'
                    net.add_edge(
                        triple['subject'], 
                        triple['object'],
                        label=triple['predicate'],
                        color=color,
                        dashes=is_inferred
                    )
                
                net.save_graph(output_path)
                return {"html_path": output_path}
        
        return DefaultVisualizer(config)
    
    async def _generate_visualization(
        self,
        visualizer,
        triples: List[Dict[str, Any]],
        output_path: Optional[str],
        tenant_id: str,
        graph_name: str
    ) -> Dict[str, Any]:
        """
        使用可视化器生成HTML
        
        Args:
            visualizer: 可视化器实例
            triples: 三元组数据
            output_path: 输出路径
            tenant_id: 租户ID
            graph_name: 图名称
            
        Returns:
            生成结果
        """
        # 生成输出路径
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            filename = f"kg_{tenant_id}_{graph_name}_{os.getpid()}.html"
            output_path = os.path.join(temp_dir, filename)
        
        # 根据可视化器类型调用相应方法
        if hasattr(visualizer, 'visualize_knowledge_graph'):
            # 核心可视化器
            result = visualizer.visualize_knowledge_graph(triples, output_path)
            
        elif hasattr(visualizer, 'create_visualization'):
            # 简单可视化器
            result_path = visualizer.create_visualization(triples, output_path)
            result = {"html_path": result_path}
            
        elif hasattr(visualizer, 'build_interactive_graph'):
            # 交互式可视化器
            result_path = visualizer.build_interactive_graph(
                triples, 
                output_path,
                title=f"知识图谱 - {tenant_id}/{graph_name}"
            )
            result = {"html_path": result_path}
            
        else:
            # 兜底处理
            raise ValueError(f"不支持的可视化器类型: {type(visualizer)}")
        
        # 读取HTML内容
        html_content = None
        if os.path.exists(output_path):
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            except Exception as e:
                self.logger.warning(f"读取HTML内容失败: {str(e)}")
        
        return {
            "html_path": output_path,
            "html_content": html_content,
            "statistics": result.get("statistics", {}) if isinstance(result, dict) else {}
        }
    
    async def get_graph_statistics(
        self, 
        tenant_id: str, 
        graph_name: str
    ) -> Dict[str, Any]:
        """
        获取图谱统计信息（用于可视化预览）
        
        Args:
            tenant_id: 租户ID
            graph_name: 图名称
            
        Returns:
            统计信息
        """
        try:
            # 从数据库获取基础统计
            if hasattr(self.graph_db, 'get_graph_statistics'):
                db_stats = await self.graph_db.get_graph_statistics(tenant_id, graph_name)
                if db_stats.get("success"):
                    return db_stats.get("statistics", {})
            
            # 如果数据库没有统计功能，则计算基础统计
            graph_data = await self.graph_db.load_knowledge_graph(tenant_id, graph_name)
            if not graph_data.get("success", False):
                return {"error": "数据加载失败"}
            
            triples = graph_data.get("triples", [])
            
            # 基础统计计算
            entities = set()
            relations = set()
            
            for triple in triples:
                if isinstance(triple, dict):
                    entities.add(triple.get("subject", ""))
                    entities.add(triple.get("object", ""))
                    relations.add(triple.get("predicate", ""))
            
            return {
                "nodes_count": len(entities),
                "edges_count": len(triples),
                "relations_count": len(relations),
                "entities": list(entities),
                "relations": list(relations)
            }
            
        except Exception as e:
            self.logger.error(f"获取图谱统计失败: {str(e)}")
            return {"error": str(e)}
    
    async def generate_networkx_graph(
        self, 
        tenant_id: str, 
        graph_name: str
    ) -> Optional[nx.Graph]:
        """
        从图数据库生成NetworkX图对象（用于高级分析）
        
        Args:
            tenant_id: 租户ID
            graph_name: 图名称
            
        Returns:
            NetworkX图对象
        """
        try:
            # 加载数据
            graph_data = await self.graph_db.load_knowledge_graph(tenant_id, graph_name)
            if not graph_data.get("success", False):
                return None
            
            triples = graph_data.get("triples", [])
            
            # 创建NetworkX图
            G = nx.Graph()
            
            for triple in triples:
                if isinstance(triple, dict):
                    subject = triple.get("subject")
                    obj = triple.get("object") 
                    predicate = triple.get("predicate")
                    
                    if subject and obj and predicate:
                        # 添加边，包含关系信息
                        if G.has_edge(subject, obj):
                            # 如果边已存在，累加关系
                            G[subject][obj]['relationships'].add(predicate)
                        else:
                            G.add_edge(subject, obj, 
                                     relationships={predicate},
                                     confidence=triple.get("confidence", 1.0),
                                     inferred=triple.get("inferred", False))
            
            self.logger.info(f"生成NetworkX图: {G.number_of_nodes()}节点, {G.number_of_edges()}边")
            return G
            
        except Exception as e:
            self.logger.error(f"生成NetworkX图失败: {str(e)}")
            return None

# 便捷函数
async def visualize_from_arangodb(
    arango_adapter: ArangoDBAdapter,
    tenant_id: str,
    graph_name: str,
    output_path: Optional[str] = None,
    visualization_type: str = "interactive"
) -> Dict[str, Any]:
    """
    从ArangoDB生成可视化的便捷函数
    
    Args:
        arango_adapter: ArangoDB适配器
        tenant_id: 租户ID
        graph_name: 图名称
        output_path: 输出路径
        visualization_type: 可视化类型
        
    Returns:
        生成结果
    """
    bridge = GraphVisualizationBridge(arango_adapter)
    return await bridge.generate_html_visualization(
        tenant_id, graph_name, output_path, visualization_type
    )

async def visualize_from_postgresql(
    pg_adapter: PostgreSQLAGEAdapter,
    tenant_id: str,
    graph_name: str,
    output_path: Optional[str] = None,
    visualization_type: str = "interactive"
) -> Dict[str, Any]:
    """
    从PostgreSQL+AGE生成可视化的便捷函数
    
    Args:
        pg_adapter: PostgreSQL适配器
        tenant_id: 租户ID
        graph_name: 图名称
        output_path: 输出路径
        visualization_type: 可视化类型
        
    Returns:
        生成结果
    """
    bridge = GraphVisualizationBridge(pg_adapter)
    return await bridge.generate_html_visualization(
        tenant_id, graph_name, output_path, visualization_type
    ) 