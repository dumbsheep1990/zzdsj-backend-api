"""
存储配置管理
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class StorageConfig:
    """
    存储配置数据类
    """
    # 向量存储配置
    vector_store_type: str = "milvus"  # milvus, elasticsearch, chroma等
    vector_store_host: str = "localhost"
    vector_store_port: int = 19530
    vector_store_collection: str = "default_collection"
    vector_dimension: int = 1536
    
    # 对象存储配置
    object_store_type: str = "minio"  # minio, s3, azure等
    object_store_endpoint: str = "localhost:9000"
    object_store_access_key: str = ""
    object_store_secret_key: str = ""
    object_store_bucket: str = "default-bucket"
    object_store_secure: bool = False
    
    # 连接配置
    connection_timeout: int = 30
    connection_retry: int = 3
    connection_pool_size: int = 10
    
    # 其他配置
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self, key, default)
    
    def update(self, **kwargs) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra_config[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if isinstance(value, dict):
                result.update(value)
            else:
                result[field_name] = value
        return result


def create_config_from_settings(settings: Any) -> StorageConfig:
    """
    从settings对象创建存储配置
    
    参数:
        settings: 配置对象
        
    返回:
        存储配置实例
    """
    config = StorageConfig()
    
    # 向量存储配置
    if hasattr(settings, 'MILVUS_HOST'):
        config.vector_store_host = settings.MILVUS_HOST
    if hasattr(settings, 'MILVUS_PORT'):
        config.vector_store_port = settings.MILVUS_PORT
    if hasattr(settings, 'MILVUS_COLLECTION'):
        config.vector_store_collection = settings.MILVUS_COLLECTION
        
    # 对象存储配置
    if hasattr(settings, 'MINIO_ENDPOINT'):
        config.object_store_endpoint = settings.MINIO_ENDPOINT
    if hasattr(settings, 'MINIO_ACCESS_KEY'):
        config.object_store_access_key = settings.MINIO_ACCESS_KEY
    if hasattr(settings, 'MINIO_SECRET_KEY'):
        config.object_store_secret_key = settings.MINIO_SECRET_KEY
    if hasattr(settings, 'MINIO_BUCKET'):
        config.object_store_bucket = settings.MINIO_BUCKET
    if hasattr(settings, 'MINIO_SECURE'):
        config.object_store_secure = settings.MINIO_SECURE
    
    return config 