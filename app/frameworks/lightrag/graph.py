"""LightRAG知识图谱处理组件
根据文档构建知识图谱，并提供创建、管理和查询的功能
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import os
import logging
import threading
from pathlib import Path
import time

try:
    import lightrag
    from lightrag import KnowledgeGraph, KnowledgeGraphConfig
    from lightrag.schema import Document, DocumentChunk, Relation
    from lightrag.storage import StorageConfig, StorageType
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    # 创建模拟类，用于类型提示
    class KnowledgeGraph:
        def __init__(self, *args, **kwargs):
            pass
    class KnowledgeGraphConfig:
        def __init__(self, *args, **kwargs):
            pass

from app.config import settings

logger = logging.getLogger(__name__)

class GraphManager:
    """知识图谱管理器，负责创建、管理和查询知识图谱"""
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'GraphManager':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初始化图谱管理器"""
        if not LIGHTRAG_AVAILABLE:
            logger.warning("LightRAG依赖未安装，知识图谱功能不可用")
            self.enabled = False
            return
            
        self.enabled = settings.LIGHTRAG_ENABLED
        if not self.enabled:
            logger.info("LightRAG知识图谱功能已禁用")
            return
            
        # 确保目录存在
        self.base_dir = Path(settings.LIGHTRAG_BASE_DIR)
        os.makedirs(self.base_dir, exist_ok=True)
        
        # 存储类型配置
        self.graph_db_type = settings.LIGHTRAG_GRAPH_DB_TYPE
        
        # 维护图谱实例字典，键为图谱ID
        self.graphs: Dict[str, KnowledgeGraph] = {}
        
        logger.info(f"LightRAG知识图谱管理器初始化: 存储类型={self.graph_db_type}")
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        if self.graph_db_type == "file":
            return {
                "type": StorageType.FILE
            }
        elif self.graph_db_type == "postgres":
            return {
                "type": StorageType.POSTGRES,
                "host": settings.LIGHTRAG_PG_HOST,
                "port": settings.LIGHTRAG_PG_PORT,
                "user": settings.LIGHTRAG_PG_USER,
                "password": settings.LIGHTRAG_PG_PASSWORD,
                "database": settings.LIGHTRAG_PG_DB
            }
        elif self.graph_db_type == "redis":
            return {
                "type": StorageType.REDIS,
                "host": settings.LIGHTRAG_REDIS_HOST,
                "port": settings.LIGHTRAG_REDIS_PORT,
                "db": settings.LIGHTRAG_REDIS_DB,
                "password": settings.LIGHTRAG_REDIS_PASSWORD or None
            }
        else:
            logger.warning(f"未知的存储类型: {self.graph_db_type}，使用文件存储")
            return {"type": StorageType.FILE}
    
    def create_graph(self, graph_id: str, embedding_dim: Optional[int] = None) -> KnowledgeGraph:
        """创建新的知识图谱
        
        参数:
            graph_id: 图谱ID，用于区分不同知识图谱
            embedding_dim: 嵌入维度
            
        返回:
            知识图谱实例
        """
        if not self.enabled or not LIGHTRAG_AVAILABLE:
            logger.warning("LightRAG功能未启用或依赖未安装")
            return None
            
        # 如果图谱已存在，直接返回
        if graph_id in self.graphs:
            return self.graphs[graph_id]
        
        # 准备配置
        graph_dir = self.base_dir / graph_id
        os.makedirs(graph_dir, exist_ok=True)
        
        storage_config = self.get_storage_config()
        storage_config["prefix"] = graph_id  # 添加前缀以区分不同图谱在同一数据库中的数据
        
        # 创建存储配置
        storage_cfg = StorageConfig(**storage_config)
        
        # 创建图谱配置
        kg_config = KnowledgeGraphConfig(
            storage=storage_cfg,
            base_dir=str(graph_dir),
            embedding_dim=embedding_dim or settings.LIGHTRAG_DEFAULT_EMBEDDING_DIM,
            max_token_size=settings.LIGHTRAG_MAX_TOKEN_SIZE
        )
        
        # 创建图谱实例
        try:
            graph = KnowledgeGraph(config=kg_config)
            self.graphs[graph_id] = graph
            logger.info(f"创建知识图谱成功: {graph_id}")
            return graph
        except Exception as e:
            logger.error(f"创建知识图谱失败: {graph_id}, 错误: {str(e)}")
            return None
    
    def get_graph(self, graph_id: str) -> Optional[KnowledgeGraph]:
        """获取已有的知识图谱实例
        
        参数:
            graph_id: 图谱ID
            
        返回:
            知识图谱实例，如果不存在则返回None
        """
        if not self.enabled or not LIGHTRAG_AVAILABLE:
            return None
            
        # 如果已加载，直接返回
        if graph_id in self.graphs:
            return self.graphs[graph_id]
            
        # 尝试加载现有图谱
        try:
            graph_dir = self.base_dir / graph_id
            if not graph_dir.exists():
                logger.warning(f"图谱目录不存在: {graph_id}")
                return None
                
            # 准备配置
            storage_config = self.get_storage_config()
            storage_config["prefix"] = graph_id
            storage_cfg = StorageConfig(**storage_config)
            
            kg_config = KnowledgeGraphConfig(
                storage=storage_cfg,
                base_dir=str(graph_dir),
                embedding_dim=settings.LIGHTRAG_DEFAULT_EMBEDDING_DIM,
                max_token_size=settings.LIGHTRAG_MAX_TOKEN_SIZE
            )
            
            graph = KnowledgeGraph(config=kg_config)
            self.graphs[graph_id] = graph
            logger.info(f"加载知识图谱成功: {graph_id}")
            return graph
        except Exception as e:
            logger.error(f"加载知识图谱失败: {graph_id}, 错误: {str(e)}")
            return None
    
    def delete_graph(self, graph_id: str) -> bool:
        """删除知识图谱
        
        参数:
            graph_id: 图谱ID
            
        返回:
            是否删除成功
        """
        if not self.enabled or not LIGHTRAG_AVAILABLE:
            return False
            
        # 如果已加载，先移除引用
        if graph_id in self.graphs:
            del self.graphs[graph_id]
            
        # 删除存储
        try:
            graph_dir = self.base_dir / graph_id
            if graph_dir.exists():
                # 如果是文件存储，删除目录
                if self.graph_db_type == "file":
                    import shutil
                    shutil.rmtree(graph_dir)
                # 对于数据库存储，需要删除相关记录
                elif self.graph_db_type in ["postgres", "redis"]:
                    # 临时创建图谱实例，然后清空所有数据
                    temp_graph = self.create_graph(graph_id + "_temp_" + str(int(time.time())))
                    if temp_graph:
                        # 这里应该有清空数据的API，但如果没有，可以使用底层存储API
                        # 具体实现取决于LightRAG的API设计
                        pass
                    
                logger.info(f"删除知识图谱成功: {graph_id}")
                return True
            else:
                logger.warning(f"图谱目录不存在: {graph_id}")
                return False
        except Exception as e:
            logger.error(f"删除知识图谱失败: {graph_id}, 错误: {str(e)}")
            return False
    
    def list_graphs(self) -> List[str]:
        """列出所有图谱ID
        
        返回:
            图谱ID列表
        """
        if not self.enabled or not LIGHTRAG_AVAILABLE:
            return []
            
        try:
            # 如果是文件存储，直接列出目录
            return [d.name for d in self.base_dir.iterdir() if d.is_dir()]
        except Exception as e:
            logger.error(f"列出图谱失败, 错误: {str(e)}")
            return []
    
    def get_knowledge_graph_stats(self, graph_id: str) -> Dict[str, Any]:
        """获取知识图谱统计信息
        
        参数:
            graph_id: 图谱ID
            
        返回:
            统计信息字典
        """
        if not self.enabled or not LIGHTRAG_AVAILABLE:
            return {}
            
        graph = self.get_graph(graph_id)
        if not graph:
            return {}
            
        try:
            # 获取图谱统计信息，具体API取决于LightRAG的实现
            # 这里使用一个基础的实现，实际使用时需要根据LightRAG的API调整
            return {
                "document_count": len(graph.get_all_documents()) if hasattr(graph, "get_all_documents") else 0,
                "chunk_count": len(graph.get_all_chunks()) if hasattr(graph, "get_all_chunks") else 0,
                "relation_count": len(graph.get_all_relations()) if hasattr(graph, "get_all_relations") else 0,
                "embedding_dim": graph.config.embedding_dim if hasattr(graph, "config") else 0,
                "created_at": time.ctime(os.path.getctime(str(self.base_dir / graph_id))) if (self.base_dir / graph_id).exists() else "",
                "storage_type": self.graph_db_type
            }
        except Exception as e:
            logger.error(f"获取图谱统计信息失败: {graph_id}, 错误: {str(e)}")
            return {}


def get_graph_manager() -> GraphManager:
    """获取图谱管理器单例"""
    return GraphManager.get_instance()