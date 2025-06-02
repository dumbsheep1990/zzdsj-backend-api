"""
向量数据库配置模块
定义系统启动时的向量数据库自动初始化配置
"""

import os
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.vector_store import VectorBackendType


class VectorDatabaseAutoInitConfig(BaseModel):
    """向量数据库自动初始化配置"""
    
    # 是否启用自动初始化
    enabled: bool = Field(True, description="是否启用向量数据库自动初始化")
    
    # 主要后端类型
    primary_backend: VectorBackendType = Field(
        VectorBackendType.MILVUS, 
        description="主要向量数据库后端类型"
    )
    
    # 备用后端类型（故障转移时使用）
    fallback_backends: List[VectorBackendType] = Field(
        default_factory=lambda: [VectorBackendType.PGVECTOR],
        description="备用向量数据库后端类型列表"
    )
    
    # 自动创建的集合列表
    auto_create_collections: List[str] = Field(
        default_factory=lambda: ["document_collection", "knowledge_base_collection"],
        description="系统启动时自动创建的集合模板列表"
    )
    
    # 初始化重试配置
    retry_attempts: int = Field(3, description="初始化重试次数")
    retry_delay: int = Field(5, description="重试间隔(秒)")
    
    # 健康检查配置
    health_check_enabled: bool = Field(True, description="是否启用健康检查")
    health_check_interval: int = Field(60, description="健康检查间隔(秒)")
    
    # 故障转移配置
    auto_failover: bool = Field(True, description="是否启用自动故障转移")
    failover_threshold: int = Field(3, description="故障转移阈值(连续失败次数)")


class MilvusConnectionConfig(BaseModel):
    """Milvus连接配置"""
    host: str = Field("localhost", description="Milvus主机地址")
    port: int = Field(19530, description="Milvus端口")
    user: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    secure: bool = Field(False, description="是否使用安全连接")
    timeout: int = Field(10, description="连接超时时间")
    
    # 从环境变量获取配置
    @classmethod
    def from_env(cls):
        return cls(
            host=os.getenv("MILVUS_HOST", "localhost"),
            port=int(os.getenv("MILVUS_PORT", "19530")),
            user=os.getenv("MILVUS_USER"),
            password=os.getenv("MILVUS_PASSWORD"),
            secure=os.getenv("MILVUS_SECURE", "false").lower() == "true",
            timeout=int(os.getenv("MILVUS_TIMEOUT", "10"))
        )


class PostgreSQLConnectionConfig(BaseModel):
    """PostgreSQL+pgvector连接配置"""
    database_url: Optional[str] = Field(None, description="PostgreSQL数据库URL")
    host: str = Field("localhost", description="PostgreSQL主机地址")
    port: int = Field(5432, description="PostgreSQL端口")
    user: str = Field("postgres", description="用户名")
    password: str = Field("password", description="密码")
    database: str = Field("postgres", description="数据库名")
    schema_name: str = Field("public", description="模式名")
    timeout: int = Field(10, description="连接超时时间")
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        if self.database_url:
            return self.database_url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @classmethod
    def from_env(cls):
        database_url = os.getenv("PGVECTOR_DATABASE_URL")
        if database_url:
            return cls(database_url=database_url)
        
        return cls(
            host=os.getenv("PGVECTOR_HOST", "localhost"),
            port=int(os.getenv("PGVECTOR_PORT", "5432")),
            user=os.getenv("PGVECTOR_USER", "postgres"),
            password=os.getenv("PGVECTOR_PASSWORD", "password"),
            database=os.getenv("PGVECTOR_DATABASE", "postgres"),
            schema_name=os.getenv("PGVECTOR_SCHEMA", "public"),
            timeout=int(os.getenv("PGVECTOR_TIMEOUT", "10"))
        )


class ElasticsearchConnectionConfig(BaseModel):
    """Elasticsearch连接配置"""
    es_url: str = Field("http://localhost:9200", description="Elasticsearch URL")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    api_key: Optional[str] = Field(None, description="API密钥")
    timeout: int = Field(30, description="连接超时时间")
    
    @classmethod
    def from_env(cls):
        return cls(
            es_url=os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
            username=os.getenv("ELASTICSEARCH_USERNAME"),
            password=os.getenv("ELASTICSEARCH_PASSWORD"),
            api_key=os.getenv("ELASTICSEARCH_API_KEY"),
            timeout=int(os.getenv("ELASTICSEARCH_TIMEOUT", "30"))
        )


class VectorDatabaseConfig(BaseModel):
    """完整的向量数据库配置"""
    
    # 自动初始化配置
    auto_init: VectorDatabaseAutoInitConfig = Field(
        default_factory=VectorDatabaseAutoInitConfig,
        description="自动初始化配置"
    )
    
    # 各后端连接配置
    milvus: MilvusConnectionConfig = Field(
        default_factory=MilvusConnectionConfig.from_env,
        description="Milvus连接配置"
    )
    
    pgvector: PostgreSQLConnectionConfig = Field(
        default_factory=PostgreSQLConnectionConfig.from_env,
        description="PostgreSQL+pgvector连接配置"
    )
    
    elasticsearch: ElasticsearchConnectionConfig = Field(
        default_factory=ElasticsearchConnectionConfig.from_env,
        description="Elasticsearch连接配置"
    )
    
    # 向量配置
    default_dimension: int = Field(1536, description="默认向量维度")
    
    # 性能配置
    batch_size: int = Field(1000, description="批量操作大小")
    max_connections: int = Field(10, description="最大连接数")
    
    @classmethod
    def from_env(cls):
        """从环境变量创建配置"""
        return cls(
            auto_init=VectorDatabaseAutoInitConfig(
                enabled=os.getenv("VECTOR_DB_AUTO_INIT", "true").lower() == "true",
                primary_backend=VectorBackendType(
                    os.getenv("VECTOR_DB_PRIMARY_BACKEND", "milvus")
                ),
                auto_create_collections=os.getenv(
                    "VECTOR_DB_AUTO_CREATE_COLLECTIONS", 
                    "document_collection,knowledge_base_collection"
                ).split(",")
            ),
            milvus=MilvusConnectionConfig.from_env(),
            pgvector=PostgreSQLConnectionConfig.from_env(),
            elasticsearch=ElasticsearchConnectionConfig.from_env(),
            default_dimension=int(os.getenv("VECTOR_DB_DEFAULT_DIMENSION", "1536")),
            batch_size=int(os.getenv("VECTOR_DB_BATCH_SIZE", "1000")),
            max_connections=int(os.getenv("VECTOR_DB_MAX_CONNECTIONS", "10"))
        )


# 全局配置实例
vector_db_config = VectorDatabaseConfig.from_env()


def get_vector_db_config() -> VectorDatabaseConfig:
    """获取向量数据库配置"""
    return vector_db_config


def get_backend_config(backend_type: VectorBackendType) -> Dict[str, Any]:
    """获取指定后端的连接配置"""
    config = get_vector_db_config()
    
    if backend_type == VectorBackendType.MILVUS:
        return config.milvus.dict()
    elif backend_type == VectorBackendType.PGVECTOR:
        return {
            "database_url": config.pgvector.get_database_url(),
            "schema_name": config.pgvector.schema_name,
            "timeout": config.pgvector.timeout
        }
    elif backend_type == VectorBackendType.ELASTICSEARCH:
        return config.elasticsearch.dict()
    else:
        raise ValueError(f"不支持的后端类型: {backend_type}")


def is_auto_init_enabled() -> bool:
    """检查是否启用了自动初始化"""
    return get_vector_db_config().auto_init.enabled


def get_primary_backend() -> VectorBackendType:
    """获取主要后端类型"""
    return get_vector_db_config().auto_init.primary_backend


def get_fallback_backends() -> List[VectorBackendType]:
    """获取备用后端类型列表"""
    return get_vector_db_config().auto_init.fallback_backends


def get_auto_create_collections() -> List[str]:
    """获取自动创建的集合列表"""
    return get_vector_db_config().auto_init.auto_create_collections 