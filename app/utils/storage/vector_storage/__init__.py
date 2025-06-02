"""
向量存储模块
提供统一的向量数据库管理接口，支持多种后端：Milvus、PostgreSQL+pgvector、Elasticsearch等
"""

# 导入核心组件
from .core.base import VectorStorage
from .core.exceptions import VectorStoreError, ConnectionError, ConfigurationError

# 导入标准化组件
from .standard_initializer import (
    StandardVectorStoreInitializer,
    VectorStoreFactory,
    init_standard_document_collection,
    init_pgvector_document_collection,
    init_elasticsearch_document_collection,
    init_knowledge_base_collection,
    init_elasticsearch_knowledge_base_collection
)

# 导入适配器
from .milvus_adapter import MilvusVectorStore
from .pgvector_adapter import PgVectorStore
from .elasticsearch_adapter import ElasticsearchVectorStore

# 导入工具函数
from .store import VectorStore, get_vector_store
from .template_loader import get_template_loader, list_available_templates

# 导入向后兼容支持
from .legacy_support import (
    init_milvus,
    get_collection,
    add_vectors,
    search_similar_vectors
)

# 导入配置模式
from app.schemas.vector_store import (
    VectorBackendType,
    VectorStoreConfig,
    StandardCollectionDefinition,
    VectorStoreInitializer,
    get_standard_document_collection,
    get_knowledge_base_collection
)

__all__ = [
    # 核心组件
    "VectorStorage",
    "VectorStoreError", 
    "ConnectionError",
    "ConfigurationError",
    
    # 标准化组件
    "StandardVectorStoreInitializer",
    "VectorStoreFactory",
    "init_standard_document_collection",
    "init_pgvector_document_collection",
    "init_elasticsearch_document_collection",
    "init_knowledge_base_collection",
    "init_elasticsearch_knowledge_base_collection",
    
    # 适配器
    "MilvusVectorStore",
    "PgVectorStore",
    "ElasticsearchVectorStore",
    
    # 工具函数
    "VectorStore",
    "get_vector_store",
    "get_template_loader",
    "list_available_templates",
    
    # 向后兼容
    "init_milvus",
    "get_collection",
    "add_vectors", 
    "search_similar_vectors",
    
    # 配置模式
    "VectorBackendType",
    "VectorStoreConfig",
    "StandardCollectionDefinition",
    "VectorStoreInitializer",
    "get_standard_document_collection",
    "get_knowledge_base_collection"
] 