"""
数据库配置检测及适配模块
用于检测和验证当前系统使用的数据库类型和连接信息
支持PostgreSQL、MySQL、SQLite以及向量数据库(Milvus, Elasticsearch)和时序数据库(InfluxDB)
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseType:
    """数据库类型枚举"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    UNKNOWN = "unknown"

class VectorStoreType:
    """向量存储类型枚举"""
    MILVUS = "milvus"
    ELASTICSEARCH = "elasticsearch"
    NONE = "none"

class TimeSeriesDBType:
    """时序数据库类型枚举"""
    INFLUXDB = "influxdb"
    NONE = "none"

def detect_database_type() -> str:
    """
    从数据库URL检测数据库类型
    
    返回:
        数据库类型字符串
    """
    db_url = settings.DATABASE_URL.lower()
    
    if db_url.startswith("postgresql") or db_url.startswith("postgres"):
        return DatabaseType.POSTGRESQL
    elif db_url.startswith("mysql"):
        return DatabaseType.MYSQL
    elif db_url.startswith("sqlite"):
        return DatabaseType.SQLITE
    else:
        logger.warning(f"未能识别数据库类型: {db_url}")
        return DatabaseType.UNKNOWN
    
def get_connection_params() -> Dict[str, Any]:
    """
    从数据库URL解析连接参数
    
    返回:
        连接参数字典
    """
    db_url = settings.DATABASE_URL
    result = {}
    
    # 提取基本连接信息
    parsed = urlparse(db_url)
    
    # 数据库类型
    db_type = detect_database_type()
    result["db_type"] = db_type
    
    # 主机和端口
    result["host"] = parsed.hostname or ""
    result["port"] = parsed.port or ""
    
    # 用户名和密码
    result["username"] = parsed.username or ""
    result["password"] = parsed.password or ""
    
    # 数据库名称
    if db_type == DatabaseType.SQLITE:
        result["database"] = parsed.path
    else:
        result["database"] = parsed.path.lstrip('/') if parsed.path else ""
    
    # 提取查询参数
    if parsed.query:
        params = parsed.query.split('&')
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)
                result[key] = value
    
    return result

def detect_vector_store_type() -> str:
    """
    检测当前配置的向量存储类型
    
    返回:
        向量存储类型字符串
    """
    # 检查Milvus配置
    if settings.MILVUS_HOST and settings.MILVUS_PORT:
        return VectorStoreType.MILVUS
    
    # 检查Elasticsearch配置
    elif settings.ELASTICSEARCH_URL:
        return VectorStoreType.ELASTICSEARCH
    
    return VectorStoreType.NONE

def detect_time_series_db() -> str:
    """
    检测时序数据库配置
    
    返回:
        时序数据库类型字符串
    """
    # 目前系统未集成InfluxDB，返回NONE
    # 当增加InfluxDB配置后可以扩展此方法
    return TimeSeriesDBType.NONE

def get_db_config() -> Dict[str, Any]:
    """
    获取完整的数据库配置
    
    返回:
        包含所有数据库配置的字典
    """
    config = {
        "main_db": {
            "type": detect_database_type(),
            "params": get_connection_params()
        },
        "vector_store": {
            "type": detect_vector_store_type(),
            "milvus": {
                "host": settings.MILVUS_HOST,
                "port": settings.MILVUS_PORT,
                "collection": settings.MILVUS_COLLECTION
            },
            "elasticsearch": {
                "url": settings.ELASTICSEARCH_URL,
                "username": settings.ELASTICSEARCH_USERNAME,
                "password": settings.ELASTICSEARCH_PASSWORD,
                "index": settings.ELASTICSEARCH_INDEX,
                "cloud_id": settings.ELASTICSEARCH_CLOUD_ID,
                "api_key": settings.ELASTICSEARCH_API_KEY
            }
        },
        "time_series_db": {
            "type": detect_time_series_db(),
            # 为将来的InfluxDB集成预留配置
            "influxdb": {}
        },
        "object_storage": {
            "type": "minio",
            "minio": {
                "endpoint": settings.MINIO_ENDPOINT,
                "access_key": settings.MINIO_ACCESS_KEY,
                "secret_key": settings.MINIO_SECRET_KEY,
                "secure": settings.MINIO_SECURE,
                "bucket": settings.MINIO_BUCKET
            }
        }
    }
    
    return config

def is_postgres() -> bool:
    """检查是否使用PostgreSQL"""
    return detect_database_type() == DatabaseType.POSTGRESQL

def is_mysql() -> bool:
    """检查是否使用MySQL"""
    return detect_database_type() == DatabaseType.MYSQL

def is_sqlite() -> bool:
    """检查是否使用SQLite"""
    return detect_database_type() == DatabaseType.SQLITE

def is_milvus_enabled() -> bool:
    """检查是否启用Milvus"""
    return detect_vector_store_type() == VectorStoreType.MILVUS

def is_elasticsearch_enabled() -> bool:
    """检查是否启用Elasticsearch"""
    return detect_vector_store_type() == VectorStoreType.ELASTICSEARCH

def is_influxdb_enabled() -> bool:
    """检查是否启用InfluxDB"""
    return detect_time_series_db() == TimeSeriesDBType.INFLUXDB
