#!/usr/bin/env python3
"""
文件存储配置模块
支持PostgreSQL、Elasticsearch、MinIO等多种存储方案
"""

import os
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

class StorageType(Enum):
    """存储类型枚举"""
    POSTGRESQL = "postgresql"
    ELASTICSEARCH = "elasticsearch"
    MINIO = "minio"
    LOCAL_FILE = "local_file"

@dataclass
class StorageConfig:
    """存储配置基类"""
    storage_type: StorageType
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: list = field(default_factory=lambda: [
        '.pdf', '.doc', '.docx', '.txt', '.md', '.rtf',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.mp3', '.wav', '.mp4', '.avi', '.mov',
        '.zip', '.rar', '.tar', '.gz'
    ])

@dataclass
class PostgreSQLStorageConfig(StorageConfig):
    """PostgreSQL存储配置"""
    host: str = "167.71.85.231"
    port: int = 5432
    database: str = "zzdsj"
    user: str = "zzdsj"
    password: str = "zzdsj123"
    
    def __post_init__(self):
        if not hasattr(self, 'storage_type') or self.storage_type is None:
            self.storage_type = StorageType.POSTGRESQL

@dataclass
class ElasticsearchStorageConfig(StorageConfig):
    """Elasticsearch存储配置"""
    hosts: list = field(default_factory=lambda: ["localhost:9200"])
    index_name: str = "zzdsj_files"
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = False
    
    def __post_init__(self):
        if not hasattr(self, 'storage_type') or self.storage_type is None:
            self.storage_type = StorageType.ELASTICSEARCH

@dataclass
class MinIOStorageConfig(StorageConfig):
    """MinIO存储配置"""
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket_name: str = "zzdsj-files"
    secure: bool = False
    
    def __post_init__(self):
        if not hasattr(self, 'storage_type') or self.storage_type is None:
            self.storage_type = StorageType.MINIO

@dataclass
class LocalFileStorageConfig(StorageConfig):
    """本地文件存储配置"""
    base_path: str = "./uploads"
    create_date_folders: bool = True
    
    def __post_init__(self):
        if not hasattr(self, 'storage_type') or self.storage_type is None:
            self.storage_type = StorageType.LOCAL_FILE

class StorageConfigManager:
    """存储配置管理器"""
    
    def __init__(self):
        self.configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """加载所有存储配置"""
        # PostgreSQL配置
        self.configs[StorageType.POSTGRESQL] = PostgreSQLStorageConfig(
            storage_type=StorageType.POSTGRESQL,
            host=os.getenv("POSTGRES_HOST", "167.71.85.231"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "zzdsj"),
            user=os.getenv("POSTGRES_USER", "zzdsj"),
            password=os.getenv("POSTGRES_PASSWORD", "zzdsj123")
        )
        
        # Elasticsearch配置
        es_hosts = os.getenv("ES_HOSTS", "localhost:9200").split(",")
        self.configs[StorageType.ELASTICSEARCH] = ElasticsearchStorageConfig(
            storage_type=StorageType.ELASTICSEARCH,
            hosts=es_hosts,
            index_name=os.getenv("ES_FILE_INDEX", "zzdsj_files"),
            username=os.getenv("ES_USERNAME"),
            password=os.getenv("ES_PASSWORD"),
            use_ssl=os.getenv("ES_USE_SSL", "false").lower() == "true"
        )
        
        # MinIO配置
        self.configs[StorageType.MINIO] = MinIOStorageConfig(
            storage_type=StorageType.MINIO,
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            bucket_name=os.getenv("MINIO_BUCKET", "zzdsj-files"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
        )
        
        # 本地文件存储配置
        self.configs[StorageType.LOCAL_FILE] = LocalFileStorageConfig(
            storage_type=StorageType.LOCAL_FILE,
            base_path=os.getenv("LOCAL_STORAGE_PATH", "./uploads"),
            create_date_folders=os.getenv("CREATE_DATE_FOLDERS", "true").lower() == "true"
        )
    
    def get_config(self, storage_type: StorageType) -> StorageConfig:
        """获取指定类型的存储配置"""
        return self.configs.get(storage_type)
    
    def get_current_config(self) -> StorageConfig:
        """获取当前使用的存储配置"""
        current_type = os.getenv("STORAGE_TYPE", "minio").lower()  # 默认使用MinIO
        try:
            storage_type = StorageType(current_type)
            return self.get_config(storage_type)
        except ValueError:
            # 如果配置的存储类型无效，默认使用MinIO
            return self.get_config(StorageType.MINIO)

# 全局配置管理器实例
storage_config_manager = StorageConfigManager()

def get_storage_config() -> StorageConfig:
    """获取当前存储配置的便捷函数"""
    return storage_config_manager.get_current_config() 