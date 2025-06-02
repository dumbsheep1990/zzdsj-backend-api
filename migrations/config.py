"""
迁移系统配置模块
提供独立的配置管理，避免循环导入
"""

import os
from typing import Dict, Any, Optional


class MigrationConfig:
    """迁移系统配置"""
    
    def __init__(self):
        """初始化迁移配置"""
        # 数据库配置
        self.database_url = self._get_database_url()
        
        # 向量数据库配置
        self.milvus_host = os.getenv("MILVUS_HOST", "localhost")
        self.milvus_port = int(os.getenv("MILVUS_PORT", "19530"))
        
        # PgVector配置
        self.pgvector_enabled = os.getenv("PGVECTOR_ENABLED", "false").lower() == "true"
        
        # 日志配置
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # 迁移配置
        self.migration_timeout = int(os.getenv("MIGRATION_TIMEOUT", "300"))  # 5分钟
        self.force_recreate = os.getenv("FORCE_RECREATE", "false").lower() == "true"
        
    def _get_database_url(self) -> str:
        """获取数据库连接URL"""
        # 优先使用完整的DATABASE_URL
        url = os.getenv("DATABASE_URL")
        if url:
            return url
        
        # 从单独的配置项构建URL
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "zzdsj")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    def get_vector_store_config(self, vector_store_type: str) -> Dict[str, Any]:
        """获取向量存储配置"""
        if vector_store_type.lower() == "milvus":
            return {
                "host": self.milvus_host,
                "port": self.milvus_port,
                "timeout": self.migration_timeout
            }
        elif vector_store_type.lower() == "pgvector":
            return {
                "database_url": self.database_url,
                "enabled": self.pgvector_enabled
            }
        else:
            return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "database_url": self.database_url,
            "milvus_host": self.milvus_host,
            "milvus_port": self.milvus_port,
            "pgvector_enabled": self.pgvector_enabled,
            "log_level": self.log_level,
            "migration_timeout": self.migration_timeout,
            "force_recreate": self.force_recreate
        }


# 全局配置实例
_migration_config: Optional[MigrationConfig] = None


def get_migration_config() -> MigrationConfig:
    """获取迁移配置实例"""
    global _migration_config
    if _migration_config is None:
        _migration_config = MigrationConfig()
    return _migration_config


def get_database_url() -> str:
    """获取数据库URL"""
    return get_migration_config().database_url


def get_vector_store_config(vector_store_type: str) -> Dict[str, Any]:
    """获取向量存储配置"""
    return get_migration_config().get_vector_store_config(vector_store_type) 