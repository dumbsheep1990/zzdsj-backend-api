"""LightRAG配置模块
管理LightRAG的相关配置参数和设置
"""

from typing import Dict, Any, Optional, Union
import os
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class LightRAGConfig:
    """管理LightRAG配置的类"""
    
    def __init__(self):
        """初始化配置类"""
        # 基本配置
        self.enabled = settings.LIGHTRAG_ENABLED
        self.base_dir = settings.LIGHTRAG_BASE_DIR
        self.embedding_dim = settings.LIGHTRAG_DEFAULT_EMBEDDING_DIM
        self.max_token_size = settings.LIGHTRAG_MAX_TOKEN_SIZE
        
        # 存储配置
        self.graph_db_type = settings.LIGHTRAG_GRAPH_DB_TYPE
        self.pg_host = settings.LIGHTRAG_PG_HOST
        self.pg_port = settings.LIGHTRAG_PG_PORT
        self.pg_user = settings.LIGHTRAG_PG_USER
        self.pg_password = settings.LIGHTRAG_PG_PASSWORD
        self.pg_db = settings.LIGHTRAG_PG_DB
        self.redis_host = settings.LIGHTRAG_REDIS_HOST
        self.redis_port = settings.LIGHTRAG_REDIS_PORT
        self.redis_db = settings.LIGHTRAG_REDIS_DB
        self.redis_password = settings.LIGHTRAG_REDIS_PASSWORD
        
        # 高级配置
        self.use_semantic_chunking = settings.LIGHTRAG_USE_SEMANTIC_CHUNKING
        self.use_knowledge_graph = settings.LIGHTRAG_USE_KNOWLEDGE_GRAPH
        self.kg_relation_threshold = settings.LIGHTRAG_KG_RELATION_THRESHOLD
        self.max_workers = settings.LIGHTRAG_MAX_WORKERS
        
        # 创建基础目录
        if self.enabled:
            os.makedirs(self.base_dir, exist_ok=True)
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置字典
        
        返回:
            存储配置字典
        """
        if self.graph_db_type == "file":
            return {
                "type": "file"
            }
        elif self.graph_db_type == "postgres":
            return {
                "type": "postgres",
                "host": self.pg_host,
                "port": self.pg_port,
                "user": self.pg_user,
                "password": self.pg_password,
                "database": self.pg_db
            }
        elif self.graph_db_type == "redis":
            return {
                "type": "redis",
                "host": self.redis_host,
                "port": self.redis_port,
                "db": self.redis_db,
                "password": self.redis_password if self.redis_password else None
            }
        else:
            # 默认使用文件存储
            logger.warning(f"未知存储类型: {self.graph_db_type}，使用文件存储")
            return {"type": "file"}
    
    def get_graph_dir(self, graph_id: str) -> Path:
        """获取图谱目录
        
        参数:
            graph_id: 图谱ID
            
        返回:
            图谱目录路径
        """
        graph_dir = Path(self.base_dir) / graph_id
        os.makedirs(graph_dir, exist_ok=True)
        return graph_dir
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典
        
        返回:
            配置字典
        """
        return {
            "enabled": self.enabled,
            "base_dir": self.base_dir,
            "embedding_dim": self.embedding_dim,
            "max_token_size": self.max_token_size,
            "graph_db_type": self.graph_db_type,
            "pg_host": self.pg_host,
            "pg_port": self.pg_port,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "use_semantic_chunking": self.use_semantic_chunking,
            "use_knowledge_graph": self.use_knowledge_graph,
            "kg_relation_threshold": self.kg_relation_threshold,
            "max_workers": self.max_workers
        }
    
    def get_graph_id_for_knowledge_base(self, knowledge_base_id: int) -> str:
        """为知识库生成图谱ID
        
        参数:
            knowledge_base_id: 知识库ID
            
        返回:
            图谱ID
        """
        return f"kb_{knowledge_base_id}"


# 全局配置实例
lightrag_config = LightRAGConfig()