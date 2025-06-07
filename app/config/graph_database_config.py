"""
图数据库配置管理
支持ArangoDB和PostgreSQL+AGE两种方案的配置
"""

import os
from typing import Dict, Any, Optional
from enum import Enum

from app.utils.storage.graph_storage.graph_database_factory import (
    GraphDatabaseType, 
    GraphStorageStrategy, 
    GraphDatabaseConfig
)

class GraphDatabaseConfigManager:
    """图数据库配置管理器"""
    
    @staticmethod
    def get_config_from_env() -> GraphDatabaseConfig:
        """从环境变量获取图数据库配置"""
        
        # 从环境变量获取数据库类型
        db_type_str = os.getenv("GRAPH_DATABASE_TYPE", "arangodb").lower()
        
        try:
            db_type = GraphDatabaseType(db_type_str)
        except ValueError:
            db_type = GraphDatabaseType.ARANGODB
        
        if db_type == GraphDatabaseType.ARANGODB:
            return GraphDatabaseConfigManager._get_arangodb_config()
        elif db_type == GraphDatabaseType.POSTGRESQL_AGE:
            return GraphDatabaseConfigManager._get_postgresql_config()
        else:
            raise ValueError(f"不支持的图数据库类型: {db_type}")
    
    @staticmethod
    def get_config_from_settings(settings) -> GraphDatabaseConfig:
        """从主配置系统获取图数据库配置"""
        
        if not getattr(settings, 'GRAPH_DATABASE_ENABLED', True):
            raise ValueError("图数据库功能已禁用")
        
        # 获取数据库类型
        db_type_str = getattr(settings, 'GRAPH_DATABASE_TYPE', 'arangodb').lower()
        
        try:
            db_type = GraphDatabaseType(db_type_str)
        except ValueError:
            db_type = GraphDatabaseType.ARANGODB
        
        if db_type == GraphDatabaseType.ARANGODB:
            return GraphDatabaseConfigManager._get_arangodb_config_from_settings(settings)
        elif db_type == GraphDatabaseType.POSTGRESQL_AGE:
            return GraphDatabaseConfigManager._get_postgresql_config_from_settings(settings)
        else:
            raise ValueError(f"不支持的图数据库类型: {db_type}")
    
    @staticmethod
    def _get_arangodb_config() -> GraphDatabaseConfig:
        """获取ArangoDB配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.ARANGODB,
            storage_strategy=GraphStorageStrategy.NATIVE,
            connection={
                "hosts": os.getenv("ARANGO_HOSTS", "http://localhost:8529"),
                "username": os.getenv("ARANGO_USERNAME", "root"),
                "password": os.getenv("ARANGO_PASSWORD", "password")
            },
            arangodb={
                "database_prefix": os.getenv("ARANGO_DB_PREFIX", "kg_tenant_"),
                "graph_name": os.getenv("ARANGO_GRAPH_NAME", "knowledge_graph"),
                "entities_collection": "entities",
                "relations_collection": "relations",
                "use_native_algorithms": os.getenv("ARANGO_USE_NATIVE", "true").lower() == "true",
                "enable_networkx": os.getenv("ARANGO_ENABLE_NETWORKX", "true").lower() == "true"
            },
            performance={
                "batch_size": int(os.getenv("ARANGO_BATCH_SIZE", "1000")),
                "connection_pool_size": int(os.getenv("ARANGO_POOL_SIZE", "10")),
                "query_timeout": int(os.getenv("ARANGO_QUERY_TIMEOUT", "30"))
            },
            isolation={
                "strategy": "database",  # ArangoDB使用数据库级别隔离
                "tenant_sharding": os.getenv("TENANT_SHARDING_STRATEGY", "user_group")
            }
        )
    
    @staticmethod
    def _get_postgresql_config() -> GraphDatabaseConfig:
        """获取PostgreSQL+AGE配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.POSTGRESQL_AGE,
            storage_strategy=GraphStorageStrategy.HYBRID,
            connection={
                "database_url": os.getenv(
                    "GRAPH_DATABASE_URL", 
                    "postgresql://postgres:password@localhost:5432/graph_db"
                )
            },
            postgresql={
                "schema_prefix": os.getenv("PG_SCHEMA_PREFIX", "kg_tenant_"),
                "graph_name": os.getenv("PG_GRAPH_NAME", "knowledge_graph"),
                "enable_age_extension": True
            },
            networkx={
                "enable_caching": os.getenv("NETWORKX_CACHE", "true").lower() == "true",
                "cache_timeout": int(os.getenv("NETWORKX_CACHE_TIMEOUT", "3600")),
                "algorithms": [
                    "centrality", "community", "clustering", "shortest_path"
                ],
                "max_cache_size": int(os.getenv("NETWORKX_MAX_CACHE", "100"))
            },
            performance={
                "connection_pool_size": int(os.getenv("PG_POOL_SIZE", "20")),
                "query_timeout": int(os.getenv("PG_QUERY_TIMEOUT", "60")),
                "batch_size": int(os.getenv("PG_BATCH_SIZE", "500"))
            },
            isolation={
                "strategy": "schema",  # PostgreSQL使用Schema级别隔离
                "tenant_sharding": os.getenv("TENANT_SHARDING_STRATEGY", "user_group")
            }
        )
    
    @staticmethod
    def _get_arangodb_config_from_settings(settings) -> GraphDatabaseConfig:
        """从主配置系统获取ArangoDB配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.ARANGODB,
            storage_strategy=GraphStorageStrategy.NATIVE,
            connection={
                "hosts": getattr(settings, "ARANGO_HOSTS", "http://localhost:8529"),
                "username": getattr(settings, "ARANGO_USERNAME", "root"),
                "password": getattr(settings, "ARANGO_PASSWORD", "password")
            },
            arangodb={
                "database_prefix": getattr(settings, "ARANGO_DB_PREFIX", "kg_tenant_"),
                "graph_name": getattr(settings, "ARANGO_GRAPH_NAME", "knowledge_graph"),
                "entities_collection": "entities",
                "relations_collection": "relations",
                "use_native_algorithms": getattr(settings, "ARANGO_USE_NATIVE", True),
                "enable_networkx": getattr(settings, "ARANGO_ENABLE_NETWORKX", True)
            },
            performance={
                "batch_size": getattr(settings, "ARANGO_BATCH_SIZE", 1000),
                "connection_pool_size": getattr(settings, "ARANGO_POOL_SIZE", 10),
                "query_timeout": getattr(settings, "ARANGO_QUERY_TIMEOUT", 30)
            },
            isolation={
                "strategy": "database",
                "tenant_sharding": getattr(settings, "TENANT_SHARDING_STRATEGY", "user_group")
            }
        )
    
    @staticmethod
    def _get_postgresql_config_from_settings(settings) -> GraphDatabaseConfig:
        """从主配置系统获取PostgreSQL+AGE配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.POSTGRESQL_AGE,
            storage_strategy=GraphStorageStrategy.HYBRID,
            connection={
                "database_url": getattr(settings, "GRAPH_DATABASE_URL", None) or getattr(settings, "DATABASE_URL", "postgresql://postgres:password@localhost:5432/graph_db")
            },
            postgresql={
                "schema_prefix": getattr(settings, "PG_SCHEMA_PREFIX", "kg_tenant_"),
                "graph_name": getattr(settings, "PG_GRAPH_NAME", "knowledge_graph"),
                "enable_age_extension": True
            },
            networkx={
                "enable_caching": getattr(settings, "NETWORKX_CACHE", True),
                "cache_timeout": getattr(settings, "NETWORKX_CACHE_TIMEOUT", 3600),
                "algorithms": [
                    "centrality", "community", "clustering", "shortest_path"
                ],
                "max_cache_size": getattr(settings, "NETWORKX_MAX_CACHE", 100)
            },
            performance={
                "connection_pool_size": 20,
                "query_timeout": 60,
                "batch_size": 500
            },
            isolation={
                "strategy": "schema",
                "tenant_sharding": getattr(settings, "TENANT_SHARDING_STRATEGY", "user_group")
            }
        )
    
    @staticmethod
    def create_custom_config(
        db_type: GraphDatabaseType,
        custom_settings: Dict[str, Any]
    ) -> GraphDatabaseConfig:
        """创建自定义配置"""
        
        # 获取默认配置
        if db_type == GraphDatabaseType.ARANGODB:
            config = GraphDatabaseConfigManager._get_arangodb_config()
        elif db_type == GraphDatabaseType.POSTGRESQL_AGE:
            config = GraphDatabaseConfigManager._get_postgresql_config()
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
        
        # 应用自定义设置
        for key, value in custom_settings.items():
            if hasattr(config, key):
                if isinstance(getattr(config, key), dict):
                    getattr(config, key).update(value)
                else:
                    setattr(config, key, value)
        
        return config

# 配置预设
class GraphDatabasePresets:
    """图数据库配置预设"""
    
    @staticmethod
    def development_arangodb() -> GraphDatabaseConfig:
        """开发环境ArangoDB配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.ARANGODB,
            storage_strategy=GraphStorageStrategy.NATIVE,
            connection={
                "hosts": "http://localhost:8529",
                "username": "root",
                "password": "dev_password"
            },
            arangodb={
                "database_prefix": "dev_kg_",
                "graph_name": "dev_graph",
                "use_native_algorithms": True,
                "enable_networkx": True
            }
        )
    
    @staticmethod
    def production_arangodb() -> GraphDatabaseConfig:
        """生产环境ArangoDB配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.ARANGODB,
            storage_strategy=GraphStorageStrategy.NATIVE,
            connection={
                "hosts": "http://arango-cluster:8529",
                "username": "admin",
                "password": os.getenv("ARANGO_PROD_PASSWORD")
            },
            arangodb={
                "database_prefix": "prod_kg_",
                "graph_name": "knowledge_graph",
                "use_native_algorithms": True,
                "enable_networkx": False  # 生产环境可能不需要NetworkX
            },
            performance={
                "batch_size": 2000,
                "connection_pool_size": 50,
                "query_timeout": 120
            }
        )
    
    @staticmethod
    def development_postgresql() -> GraphDatabaseConfig:
        """开发环境PostgreSQL+AGE配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.POSTGRESQL_AGE,
            storage_strategy=GraphStorageStrategy.HYBRID,
            connection={
                "database_url": "postgresql://postgres:dev_password@localhost:5432/dev_graph"
            },
            postgresql={
                "schema_prefix": "dev_kg_",
                "graph_name": "dev_graph"
            },
            networkx={
                "enable_caching": True,
                "cache_timeout": 1800,  # 30分钟
                "algorithms": ["centrality", "community"]
            }
        )
    
    @staticmethod
    def production_postgresql() -> GraphDatabaseConfig:
        """生产环境PostgreSQL+AGE配置"""
        return GraphDatabaseConfig(
            db_type=GraphDatabaseType.POSTGRESQL_AGE,
            storage_strategy=GraphStorageStrategy.HYBRID,
            connection={
                "database_url": os.getenv("GRAPH_DATABASE_PROD_URL")
            },
            postgresql={
                "schema_prefix": "prod_kg_",
                "graph_name": "knowledge_graph"
            },
            networkx={
                "enable_caching": True,
                "cache_timeout": 7200,  # 2小时
                "algorithms": ["centrality", "community", "clustering", "shortest_path"],
                "max_cache_size": 500
            },
            performance={
                "connection_pool_size": 100,
                "query_timeout": 300,
                "batch_size": 1000
            }
        )

# 便捷函数
def get_graph_database_config(environment: str = "auto", settings=None) -> GraphDatabaseConfig:
    """获取图数据库配置"""
    
    if environment == "auto":
        # 优先从主配置系统获取
        if settings is not None:
            return GraphDatabaseConfigManager.get_config_from_settings(settings)
        else:
            # 回退到环境变量
            return GraphDatabaseConfigManager.get_config_from_env()
    
    elif environment == "dev_arango":
        return GraphDatabasePresets.development_arangodb()
    
    elif environment == "prod_arango":
        return GraphDatabasePresets.production_arangodb()
    
    elif environment == "dev_postgresql":
        return GraphDatabasePresets.development_postgresql()
    
    elif environment == "prod_postgresql":
        return GraphDatabasePresets.production_postgresql()
    
    else:
        raise ValueError(f"未知环境配置: {environment}")

def get_graph_database_config_from_app() -> GraphDatabaseConfig:
    """从应用配置获取图数据库配置"""
    try:
        from app.config import settings
        return get_graph_database_config("auto", settings)
    except Exception:
        # 回退到环境变量
        return get_graph_database_config("auto")

# 配置验证
def validate_graph_config(config: GraphDatabaseConfig) -> Dict[str, Any]:
    """验证图数据库配置"""
    issues = []
    
    # 检查连接配置
    if not config.connection_config:
        issues.append("缺少连接配置")
    
    if config.db_type == GraphDatabaseType.ARANGODB:
        if "hosts" not in config.connection_config:
            issues.append("ArangoDB缺少hosts配置")
        if "username" not in config.connection_config:
            issues.append("ArangoDB缺少username配置")
    
    elif config.db_type == GraphDatabaseType.POSTGRESQL_AGE:
        if "database_url" not in config.connection_config:
            issues.append("PostgreSQL缺少database_url配置")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "config_summary": {
            "db_type": config.db_type.value,
            "storage_strategy": config.storage_strategy.value,
            "has_connection": bool(config.connection_config),
            "has_performance": bool(config.performance_config)
        }
    } 