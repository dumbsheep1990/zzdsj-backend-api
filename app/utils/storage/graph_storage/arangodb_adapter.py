"""
ArangoDB图数据库适配器
提供多租户数据隔离的知识图谱存储解决方案
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    from arango import ArangoClient
    from arango.database import StandardDatabase
    from arango.graph import Graph
    ARANGO_AVAILABLE = True
except ImportError:
    ARANGO_AVAILABLE = False

from app.config import settings
from .graph_database_factory import IGraphDatabase, GraphDatabaseConfig

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger(__name__)

class ArangoGraphDatabase(IGraphDatabase):
    """ArangoDB图数据库服务"""
    
    def __init__(self, config: GraphDatabaseConfig):
        """初始化ArangoDB连接"""
        if not ARANGO_AVAILABLE:
            raise ImportError("ArangoDB Python客户端未安装，请运行: pip install python-arango")
        
        self.config = config
        self.client = None
        self.sys_db = None
        self._tenant_dbs = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # NetworkX集成配置
        self.use_networkx_algorithms = config.arangodb_config.get("enable_networkx", True)
        self.networkx_cache = {} if self.use_networkx_algorithms else None
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "hosts": getattr(settings, "ARANGO_HOSTS", "http://localhost:8529"),
            "username": getattr(settings, "ARANGO_USERNAME", "root"),
            "password": getattr(settings, "ARANGO_PASSWORD", "password"),
            "database_prefix": getattr(settings, "ARANGO_DB_PREFIX", "kg_tenant_"),
            "graph_name": "knowledge_graph",
            "entities_collection": "entities",
            "relations_collection": "relations"
        }
    
    async def initialize(self):
        """初始化数据库连接"""
        try:
            # 创建ArangoDB客户端
            self.client = ArangoClient(hosts=self.config.connection_config["hosts"])
            
            # 连接系统数据库
            self.sys_db = self.client.db(
                "_system",
                username=self.config.connection_config["username"],
                password=self.config.connection_config["password"]
            )
            
            logger.info("ArangoDB连接初始化成功")
            
        except Exception as e:
            logger.error(f"ArangoDB初始化失败: {str(e)}")
            raise
    
    async def create_tenant_context(self, tenant_id: str) -> StandardDatabase:
        """为租户创建独立数据库"""
        try:
            db_name = f"{self.config.arangodb_config['database_prefix']}{tenant_id}"
            
            # 检查数据库是否已存在
            if not self.sys_db.has_database(db_name):
                # 创建租户数据库
                self.sys_db.create_database(db_name)
                logger.info(f"创建租户数据库: {db_name}")
            
            # 连接租户数据库
            tenant_db = self.client.db(
                db_name,
                username=self.config.connection_config["username"],
                password=self.config.connection_config["password"]
            )
            
            # 初始化图结构
            await self._initialize_graph_structure(tenant_db)
            
            # 缓存数据库连接
            self._tenant_dbs[tenant_id] = tenant_db
            
            return tenant_db
            
        except Exception as e:
            logger.error(f"创建租户数据库失败 {tenant_id}: {str(e)}")
            raise
    
    async def _initialize_graph_structure(self, db: StandardDatabase):
        """初始化图结构"""
        try:
            graph_name = self.config.arangodb_config["graph_name"]
            entities_collection = self.config.arangodb_config.get("entities_collection", "entities")
            relations_collection = self.config.arangodb_config.get("relations_collection", "relations")
            
            # 创建图对象
            if not db.has_graph(graph_name):
                graph = db.create_graph(graph_name)
                
                # 创建顶点集合(实体)
                if not db.has_collection(entities_collection):
                    graph.create_vertex_collection(entities_collection)
                
                # 创建边集合(关系)
                if not db.has_collection(relations_collection):
                    graph.create_edge_definition(
                        edge_collection=relations_collection,
                        from_vertex_collections=[entities_collection],
                        to_vertex_collections=[entities_collection]
                    )
                
                logger.info(f"图结构初始化完成: {graph_name}")
            
        except Exception as e:
            logger.error(f"图结构初始化失败: {str(e)}")
            raise
    
    async def get_tenant_database(self, tenant_id: str) -> StandardDatabase:
        """获取租户数据库连接"""
        if tenant_id not in self._tenant_dbs:
            await self.create_tenant_context(tenant_id)
        
        return self._tenant_dbs[tenant_id]
    
    async def save_knowledge_graph(
        self, 
        tenant_id: str, 
        graph_id: str, 
        triples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """保存知识图谱到租户数据库"""
        try:
            tenant_db = await self.get_tenant_database(tenant_id)
            graph = tenant_db.graph(self.config.arangodb_config["graph_name"])
            
            # 提取实体和关系
            entities = self._extract_entities(triples)
            relations = self._extract_relations(triples, graph_id)
            
            # 批量插入实体
            entities_result = await self._batch_insert_entities(graph, entities)
            
            # 批量插入关系
            relations_result = await self._batch_insert_relations(graph, relations)
            
            return {
                "success": True,
                "graph_id": graph_id,
                "tenant_id": tenant_id,
                "entities_inserted": entities_result.get("inserted", 0),
                "relations_inserted": relations_result.get("inserted", 0),
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"保存知识图谱失败 {tenant_id}/{graph_id}: {str(e)}")
            raise
    
    def _extract_entities(self, triples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从三元组提取唯一实体"""
        entities = {}
        
        for triple in triples:
            subject = triple["subject"]
            object_entity = triple["object"]
            
            # 处理主语实体
            if subject not in entities:
                entities[subject] = {
                    "_key": self._generate_entity_key(subject),
                    "name": subject,
                    "entity_type": triple.get("subject_type", "entity"),
                    "confidence": triple.get("confidence", 1.0),
                    "created_at": datetime.utcnow().isoformat(),
                    "properties": {}
                }
            
            # 处理宾语实体
            if object_entity not in entities:
                entities[object_entity] = {
                    "_key": self._generate_entity_key(object_entity),
                    "name": object_entity,
                    "entity_type": triple.get("object_type", "entity"),
                    "confidence": triple.get("confidence", 1.0),
                    "created_at": datetime.utcnow().isoformat(),
                    "properties": {}
                }
        
        return list(entities.values())
    
    def _extract_relations(self, triples: List[Dict[str, Any]], graph_id: str) -> List[Dict[str, Any]]:
        """从三元组提取关系"""
        relations = []
        
        entities_collection = self.config.arangodb_config.get("entities_collection", "entities")
        
        for i, triple in enumerate(triples):
            relation = {
                "_key": f"{graph_id}_{i}",
                "_from": f"{entities_collection}/{self._generate_entity_key(triple['subject'])}",
                "_to": f"{entities_collection}/{self._generate_entity_key(triple['object'])}",
                "relation_type": triple["predicate"],
                "confidence": triple.get("confidence", 1.0),
                "graph_id": graph_id,
                "created_at": datetime.utcnow().isoformat(),
                "properties": triple.get("properties", {})
            }
            relations.append(relation)
        
        return relations
    
    def _generate_entity_key(self, entity_name: str) -> str:
        """生成实体的唯一键"""
        import hashlib
        return hashlib.md5(entity_name.encode('utf-8')).hexdigest()
    
    async def _batch_insert_entities(
        self, 
        graph: Graph, 
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批量插入实体"""
        try:
            entities_collection = graph.vertex_collection(self.config["entities_collection"])
            
            # 使用批量插入
            result = entities_collection.insert_many(entities, silent=True, overwrite=True)
            
            return {
                "inserted": len([r for r in result if not r.get("error")]),
                "errors": [r for r in result if r.get("error")]
            }
            
        except Exception as e:
            logger.error(f"批量插入实体失败: {str(e)}")
            raise
    
    async def _batch_insert_relations(
        self, 
        graph: Graph, 
        relations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批量插入关系"""
        try:
            relations_collection = graph.edge_collection(self.config["relations_collection"])
            
            # 使用批量插入
            result = relations_collection.insert_many(relations, silent=True, overwrite=True)
            
            return {
                "inserted": len([r for r in result if not r.get("error")]),
                "errors": [r for r in result if r.get("error")]
            }
            
        except Exception as e:
            logger.error(f"批量插入关系失败: {str(e)}")
            raise
    
    async def load_knowledge_graph(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Dict[str, Any]:
        """加载知识图谱数据"""
        try:
            tenant_db = await self.get_tenant_database(tenant_id)
            
            # AQL查询获取图谱数据
            query = """
            FOR relation IN @@relations_collection
                FILTER relation.graph_id == @graph_id
                LET source = DOCUMENT(relation._from)
                LET target = DOCUMENT(relation._to)
                RETURN {
                    "subject": source.name,
                    "predicate": relation.relation_type,
                    "object": target.name,
                    "confidence": relation.confidence,
                    "properties": relation.properties
                }
            """
            
            cursor = tenant_db.aql.execute(
                query,
                bind_vars={
                    "@relations_collection": self.config["relations_collection"],
                    "graph_id": graph_id
                }
            )
            
            triples = list(cursor)
            
            return {
                "success": True,
                "graph_id": graph_id,
                "tenant_id": tenant_id,
                "triples": triples,
                "total_triples": len(triples)
            }
            
        except Exception as e:
            logger.error(f"加载知识图谱失败 {tenant_id}/{graph_id}: {str(e)}")
            raise
    
    async def delete_knowledge_graph(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Dict[str, Any]:
        """删除知识图谱"""
        try:
            tenant_db = await self.get_tenant_database(tenant_id)
            
            # 删除关系
            delete_relations_query = """
            FOR relation IN @@relations_collection
                FILTER relation.graph_id == @graph_id
                REMOVE relation IN @@relations_collection
            """
            
            tenant_db.aql.execute(
                delete_relations_query,
                bind_vars={
                    "@relations_collection": self.config["relations_collection"],
                    "graph_id": graph_id
                }
            )
            
            return {
                "success": True,
                "message": f"知识图谱 {graph_id} 已删除"
            }
            
        except Exception as e:
            logger.error(f"删除知识图谱失败 {tenant_id}/{graph_id}: {str(e)}")
            raise
    
    async def get_subgraph(
        self, 
        tenant_id: str, 
        center_entity: str, 
        depth: int = 2,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取以指定实体为中心的子图"""
        try:
            tenant_db = await self.get_tenant_database(tenant_id)
            
            # AQL查询获取子图
            query = f"""
            FOR vertex, edge, path IN 1..{depth} OUTBOUND
                (FOR e IN @@entities_collection FILTER e.name == @center_entity RETURN e)[0]
                GRAPH @graph_name
                LIMIT @limit
                RETURN {{
                    "subject": path.vertices[0].name,
                    "predicate": path.edges[0].relation_type,
                    "object": vertex.name,
                    "depth": LENGTH(path.edges)
                }}
            """
            
            cursor = tenant_db.aql.execute(
                query,
                bind_vars={
                    "@entities_collection": self.config["entities_collection"],
                    "graph_name": self.config["graph_name"],
                    "center_entity": center_entity,
                    "limit": limit
                }
            )
            
            subgraph = list(cursor)
            
            return {
                "success": True,
                "center_entity": center_entity,
                "subgraph": subgraph,
                "depth": depth,
                "total_nodes": len(subgraph)
            }
            
        except Exception as e:
            logger.error(f"获取子图失败 {tenant_id}: {str(e)}")
            raise
    
    async def get_graph_statistics(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Dict[str, Any]:
        """获取图谱统计信息"""
        try:
            tenant_db = await self.get_tenant_database(tenant_id)
            
            # 统计实体数量
            entities_query = """
            FOR relation IN @@relations_collection
                FILTER relation.graph_id == @graph_id
                COLLECT entity = relation._from
                RETURN entity
            UNION
            FOR relation IN @@relations_collection
                FILTER relation.graph_id == @graph_id
                COLLECT entity = relation._to
                RETURN entity
            """
            
            entities_cursor = tenant_db.aql.execute(
                entities_query,
                bind_vars={
                    "@relations_collection": self.config["relations_collection"],
                    "graph_id": graph_id
                }
            )
            
            unique_entities = len(list(entities_cursor))
            
            # 统计关系数量
            relations_query = """
            FOR relation IN @@relations_collection
                FILTER relation.graph_id == @graph_id
                COLLECT WITH COUNT INTO relation_count
                RETURN relation_count
            """
            
            relations_cursor = tenant_db.aql.execute(
                relations_query,
                bind_vars={
                    "@relations_collection": self.config["relations_collection"],
                    "graph_id": graph_id
                }
            )
            
            relation_count = list(relations_cursor)[0] if relations_cursor else 0
            
            # 计算图密度
            max_edges = unique_entities * (unique_entities - 1) if unique_entities > 1 else 1
            density = relation_count / max_edges if max_edges > 0 else 0
            
            return {
                "total_entities": unique_entities,
                "total_relations": relation_count,
                "graph_density": density,
                "avg_degree": (2 * relation_count) / unique_entities if unique_entities > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取图谱统计失败 {tenant_id}/{graph_id}: {str(e)}")
            raise
    
    async def export_to_networkx(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Any:
        """导出为NetworkX图对象"""
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX未安装，请运行: pip install networkx")
        
        try:
            # 检查缓存
            cache_key = f"{tenant_id}_{graph_id}"
            if self.networkx_cache and cache_key in self.networkx_cache:
                return self.networkx_cache[cache_key]
            
            # 从ArangoDB加载数据
            graph_data = await self.load_knowledge_graph(tenant_id, graph_id)
            triples = graph_data.get("triples", [])
            
            # 创建NetworkX图
            G = nx.DiGraph()
            
            # 添加节点和边
            for triple in triples:
                subject = triple["subject"]
                obj = triple["object"]
                predicate = triple["predicate"]
                
                # 添加节点
                if not G.has_node(subject):
                    G.add_node(subject, entity_type="entity")
                if not G.has_node(obj):
                    G.add_node(obj, entity_type="entity")
                
                # 添加边
                G.add_edge(
                    subject, 
                    obj, 
                    relation_type=predicate,
                    confidence=triple.get("confidence", 1.0)
                )
            
            # 缓存结果
            if self.networkx_cache:
                self.networkx_cache[cache_key] = G
            
            return G
            
        except Exception as e:
            logger.error(f"导出NetworkX图失败 {tenant_id}/{graph_id}: {str(e)}")
            raise
    
    async def compute_advanced_metrics(
        self, 
        tenant_id: str, 
        graph_id: str,
        algorithms: List[str] = None
    ) -> Dict[str, Any]:
        """使用NetworkX计算高级图指标"""
        if not NETWORKX_AVAILABLE:
            return {"error": "NetworkX不可用"}
        
        try:
            G = await self.export_to_networkx(tenant_id, graph_id)
            results = {}
            
            # 默认算法
            if not algorithms:
                algorithms = ["centrality", "community", "clustering"]
            
            # 中心性算法
            if "centrality" in algorithms:
                results["centrality"] = {
                    "betweenness": dict(nx.betweenness_centrality(G)),
                    "closeness": dict(nx.closeness_centrality(G)),
                    "degree": dict(nx.degree_centrality(G)),
                    "eigenvector": dict(nx.eigenvector_centrality(G, max_iter=1000))
                }
            
            # 社区检测
            if "community" in algorithms:
                # 转换为无向图进行社区检测
                G_undirected = G.to_undirected()
                try:
                    import networkx.algorithms.community as nx_comm
                    communities = nx_comm.greedy_modularity_communities(G_undirected)
                    results["communities"] = [list(community) for community in communities]
                    results["modularity"] = nx_comm.modularity(G_undirected, communities)
                except ImportError:
                    results["communities"] = []
                    results["modularity"] = 0.0
            
            # 聚类系数
            if "clustering" in algorithms:
                results["clustering"] = {
                    "average_clustering": nx.average_clustering(G.to_undirected()),
                    "transitivity": nx.transitivity(G.to_undirected())
                }
            
            # 路径分析
            if "paths" in algorithms:
                if nx.is_connected(G.to_undirected()):
                    results["paths"] = {
                        "average_shortest_path": nx.average_shortest_path_length(G.to_undirected()),
                        "diameter": nx.diameter(G.to_undirected())
                    }
                else:
                    results["paths"] = {
                        "connected": False,
                        "components": nx.number_connected_components(G.to_undirected())
                    }
            
            return results
            
        except Exception as e:
            logger.error(f"计算高级图指标失败 {tenant_id}/{graph_id}: {str(e)}")
            return {"error": str(e)}
    
    async def close(self):
        """关闭数据库连接"""
        try:
            if self._executor:
                self._executor.shutdown(wait=True)
            
            # 清空NetworkX缓存
            if self.networkx_cache:
                self.networkx_cache.clear()
            
            # ArangoDB客户端会自动管理连接池
            self._tenant_dbs.clear()
            
            logger.info("ArangoDB连接已关闭")
            
        except Exception as e:
            logger.error(f"关闭ArangoDB连接失败: {str(e)}")

# 全局实例
_arango_instance = None

async def get_arango_graph_db() -> ArangoGraphDatabase:
    """获取ArangoDB图数据库实例"""
    global _arango_instance
    
    if _arango_instance is None:
        _arango_instance = ArangoGraphDatabase()
        await _arango_instance.initialize()
    
    return _arango_instance

# 租户隔离管理器
class TenantIsolationManager:
    """租户隔离管理器"""
    
    def __init__(self, strategy: str = "database"):
        self.strategy = strategy
        self.tenant_cache = {}
    
    async def get_tenant_context(self, user_id: int) -> str:
        """获取用户租户上下文"""
        tenant_id = self._calculate_tenant_id(user_id)
        return tenant_id
    
    def _calculate_tenant_id(self, user_id: int) -> str:
        """计算租户ID"""
        # 简单分片策略：每1000用户一个租户
        tenant_group = user_id // 1000
        return f"group_{tenant_group}"

# 全局租户管理器
tenant_manager = TenantIsolationManager("database") 