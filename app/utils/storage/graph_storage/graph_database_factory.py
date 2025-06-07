"""
图数据库工厂类
支持多种图数据库后端的统一抽象层
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class GraphDatabaseType(Enum):
    """图数据库类型枚举"""
    ARANGODB = "arangodb"
    POSTGRESQL_AGE = "postgresql_age"
    NEO4J = "neo4j"  # 保留，以防将来支持企业版

class GraphStorageStrategy(Enum):
    """图存储策略"""
    HYBRID = "hybrid"          # 存储+计算分离
    NATIVE = "native"          # 原生图数据库
    MEMORY_CACHED = "cached"   # 内存缓存增强

class IGraphDatabase(ABC):
    """图数据库抽象接口"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化数据库连接"""
        pass
    
    @abstractmethod
    async def create_tenant_context(self, tenant_id: str) -> Any:
        """创建租户上下文"""
        pass
    
    @abstractmethod
    async def save_knowledge_graph(
        self, 
        tenant_id: str, 
        graph_id: str, 
        triples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """保存知识图谱"""
        pass
    
    @abstractmethod
    async def load_knowledge_graph(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Dict[str, Any]:
        """加载知识图谱"""
        pass
    
    @abstractmethod
    async def delete_knowledge_graph(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Dict[str, Any]:
        """删除知识图谱"""
        pass
    
    @abstractmethod
    async def get_subgraph(
        self, 
        tenant_id: str, 
        center_entity: str, 
        depth: int = 2,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取子图"""
        pass
    
    @abstractmethod
    async def get_graph_statistics(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Dict[str, Any]:
        """获取图统计信息"""
        pass
    
    @abstractmethod
    async def export_to_networkx(
        self, 
        tenant_id: str, 
        graph_id: str
    ) -> Any:
        """导出为NetworkX图对象"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass

class GraphDatabaseConfig:
    """图数据库配置类"""
    
    def __init__(self, 
                 db_type: GraphDatabaseType = GraphDatabaseType.ARANGODB,
                 storage_strategy: GraphStorageStrategy = GraphStorageStrategy.HYBRID,
                 **kwargs):
        self.db_type = db_type
        self.storage_strategy = storage_strategy
        self.connection_config = kwargs.get("connection", {})
        self.performance_config = kwargs.get("performance", {})
        self.isolation_config = kwargs.get("isolation", {})
        
        # 特定配置
        if db_type == GraphDatabaseType.ARANGODB:
            self.arangodb_config = kwargs.get("arangodb", {})
        elif db_type == GraphDatabaseType.POSTGRESQL_AGE:
            self.postgresql_config = kwargs.get("postgresql", {})
            self.networkx_config = kwargs.get("networkx", {})

class GraphDatabaseFactory:
    """图数据库工厂类"""
    
    @staticmethod
    async def create_graph_database(config: GraphDatabaseConfig) -> IGraphDatabase:
        """根据配置创建图数据库实例"""
        
        if config.db_type == GraphDatabaseType.ARANGODB:
            from .arangodb_adapter import ArangoGraphDatabase
            return ArangoGraphDatabase(config)
            
        elif config.db_type == GraphDatabaseType.POSTGRESQL_AGE:
            from .postgresql_age_adapter import PostgreSQLAGEGraphDatabase
            return PostgreSQLAGEGraphDatabase(config)
            
        elif config.db_type == GraphDatabaseType.NEO4J:
            from .neo4j_adapter import Neo4jGraphDatabase
            return Neo4jGraphDatabase(config)
        
        else:
            raise ValueError(f"不支持的图数据库类型: {config.db_type}")
    
    @staticmethod
    def get_default_config(db_type: GraphDatabaseType) -> GraphDatabaseConfig:
        """获取默认配置"""
        
        if db_type == GraphDatabaseType.ARANGODB:
            return GraphDatabaseConfig(
                db_type=GraphDatabaseType.ARANGODB,
                storage_strategy=GraphStorageStrategy.NATIVE,
                connection={
                    "hosts": "http://localhost:8529",
                    "username": "root",
                    "password": "password"
                },
                arangodb={
                    "database_prefix": "kg_tenant_",
                    "graph_name": "knowledge_graph",
                    "use_native_algorithms": True
                }
            )
        
        elif db_type == GraphDatabaseType.POSTGRESQL_AGE:
            return GraphDatabaseConfig(
                db_type=GraphDatabaseType.POSTGRESQL_AGE,
                storage_strategy=GraphStorageStrategy.HYBRID,
                connection={
                    "database_url": "postgresql://user:password@localhost:5432/database"
                },
                postgresql={
                    "schema_prefix": "kg_tenant_",
                    "graph_name": "knowledge_graph"
                },
                networkx={
                    "enable_caching": True,
                    "cache_timeout": 3600,
                    "algorithms": ["centrality", "community", "shortest_path"]
                }
            )
        
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

# 全局图数据库管理器
class GraphDatabaseManager:
    """图数据库管理器"""
    
    def __init__(self):
        self._instances = {}
        self._current_config = None
        self._current_instance = None
    
    async def initialize(self, config: GraphDatabaseConfig):
        """初始化图数据库"""
        self._current_config = config
        
        if config.db_type.value not in self._instances:
            instance = await GraphDatabaseFactory.create_graph_database(config)
            await instance.initialize()
            self._instances[config.db_type.value] = instance
        
        self._current_instance = self._instances[config.db_type.value]
        logger.info(f"图数据库初始化完成: {config.db_type.value}")
    
    async def get_database(self) -> IGraphDatabase:
        """获取当前图数据库实例"""
        if not self._current_instance:
            raise RuntimeError("图数据库未初始化")
        return self._current_instance
    
    async def switch_database(self, config: GraphDatabaseConfig):
        """切换图数据库"""
        await self.initialize(config)
    
    async def close_all(self):
        """关闭所有数据库连接"""
        for instance in self._instances.values():
            await instance.close()
        self._instances.clear()

# 全局实例
graph_db_manager = GraphDatabaseManager()

# 便捷函数
async def get_graph_database() -> IGraphDatabase:
    """获取当前图数据库实例"""
    return await graph_db_manager.get_database()

async def initialize_graph_database(db_type: GraphDatabaseType = None, **kwargs):
    """初始化图数据库"""
    from app.config import settings
    
    # 从配置或参数确定数据库类型
    if not db_type:
        db_type_str = getattr(settings, "GRAPH_DATABASE_TYPE", "arangodb").lower()
        db_type = GraphDatabaseType(db_type_str)
    
    # 获取配置
    config = GraphDatabaseFactory.get_default_config(db_type)
    
    # 应用自定义配置
    if kwargs:
        for key, value in kwargs.items():
            setattr(config, key, value)
    
    await graph_db_manager.initialize(config)
    return await graph_db_manager.get_database() 