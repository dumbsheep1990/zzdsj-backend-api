"""
向量数据库标准配置模式定义
提供集合创建、字段定义、元数据配置的标准格式
支持多种向量数据库后端：Milvus、PostgreSQL+pgvector、Elasticsearch等
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class VectorBackendType(str, Enum):
    """向量数据库后端类型枚举"""
    MILVUS = "milvus"
    PGVECTOR = "pgvector"
    ELASTICSEARCH = "elasticsearch"
    CHROMA = "chroma"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"


class VectorFieldType(str, Enum):
    """向量字段类型枚举"""
    PRIMARY_KEY = "primary_key"
    VECTOR = "vector"
    SCALAR = "scalar"
    JSON = "json"


class DataType(str, Enum):
    """数据类型枚举"""
    # 通用类型
    INT64 = "INT64"
    VARCHAR = "VARCHAR"
    FLOAT_VECTOR = "FLOAT_VECTOR"
    JSON = "JSON"
    BOOL = "BOOL"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    # PostgreSQL特定类型
    VECTOR = "VECTOR"
    TEXT = "TEXT"
    JSONB = "JSONB"
    UUID = "UUID"
    TIMESTAMP = "TIMESTAMP"
    SERIAL = "SERIAL"
    # Elasticsearch特定类型
    DENSE_VECTOR = "DENSE_VECTOR"
    KEYWORD = "KEYWORD"
    DATE = "DATE"
    OBJECT = "OBJECT"
    LONG = "LONG"


class IndexType(str, Enum):
    """索引类型枚举"""
    # Milvus索引类型
    HNSW = "HNSW"
    IVF_FLAT = "IVF_FLAT"
    IVF_SQ8 = "IVF_SQ8"
    IVF_PQ = "IVF_PQ"
    AUTOINDEX = "AUTOINDEX"
    # PostgreSQL/pgvector索引类型
    IVFFLAT = "IVFFLAT"
    HNSW_PG = "HNSW_PG"  # pgvector的HNSW
    BTREE = "BTREE"
    GIN = "GIN"
    GIST = "GIST"
    # Elasticsearch索引类型
    DENSE_VECTOR = "DENSE_VECTOR"
    KNN = "KNN"


class MetricType(str, Enum):
    """距离度量类型枚举"""
    # 通用度量类型
    L2 = "L2"
    IP = "IP"
    COSINE = "COSINE"
    HAMMING = "HAMMING"
    JACCARD = "JACCARD"
    # PostgreSQL/pgvector度量类型
    L2_PG = "vector_l2_ops"
    IP_PG = "vector_ip_ops"
    COSINE_PG = "vector_cosine_ops"
    # Elasticsearch度量类型
    COSINE_ES = "cosine"
    DOT_PRODUCT_ES = "dot_product"
    L2_NORM_ES = "l2_norm"


class FieldSchema(BaseModel):
    """字段模式定义"""
    name: str = Field(..., description="字段名称")
    data_type: DataType = Field(..., description="数据类型")
    is_primary: bool = Field(False, description="是否为主键")
    auto_id: bool = Field(False, description="是否自动生成ID")
    max_length: Optional[int] = Field(None, description="字符串字段最大长度")
    dimension: Optional[int] = Field(None, description="向量维度")
    description: Optional[str] = Field(None, description="字段描述")
    nullable: bool = Field(True, description="是否可为空")
    default_value: Optional[Any] = Field(None, description="默认值")
    # PostgreSQL特定属性
    constraint: Optional[str] = Field(None, description="字段约束")
    check: Optional[str] = Field(None, description="检查约束")


class IndexParameters(BaseModel):
    """索引参数配置"""
    index_type: IndexType = Field(IndexType.HNSW, description="索引类型")
    metric_type: MetricType = Field(MetricType.COSINE, description="距离度量类型")
    params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "M": 16,
            "efConstruction": 200
        },
        description="索引特定参数"
    )


class CollectionSchema(BaseModel):
    """集合模式定义"""
    name: str = Field(..., description="集合名称")
    description: Optional[str] = Field(None, description="集合描述")
    fields: List[FieldSchema] = Field(..., description="字段列表")
    enable_dynamic_field: bool = Field(False, description="是否启用动态字段")
    auto_id: bool = Field(False, description="是否自动生成ID")


class PartitionConfig(BaseModel):
    """分区配置"""
    enabled: bool = Field(True, description="是否启用分区")
    partition_key: Optional[str] = Field("knowledge_base_id", description="分区键字段")
    default_partitions: List[str] = Field(
        default_factory=lambda: ["_default"],
        description="默认分区列表"
    )


class VectorStoreConfig(BaseModel):
    """向量存储配置"""
    # 通用配置
    backend_type: VectorBackendType = Field(VectorBackendType.MILVUS, description="后端类型")
    collection_name: str = Field("document_vectors", description="集合/表名称")
    dimension: int = Field(1536, description="向量维度")
    connection_alias: str = Field("default", description="连接别名")
    
    # Milvus特定配置
    host: Optional[str] = Field("localhost", description="主机地址")
    port: Optional[int] = Field(19530, description="端口")
    secure: bool = Field(False, description="是否使用安全连接")
    user: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    timeout: int = Field(10, description="连接超时时间(秒)")
    
    # PostgreSQL/pgvector特定配置
    database_url: Optional[str] = Field(None, description="PostgreSQL数据库URL")
    schema_name: Optional[str] = Field("public", description="PostgreSQL模式名")
    table_name: Optional[str] = Field(None, description="PostgreSQL表名")
    
    # Elasticsearch特定配置
    es_url: Optional[str] = Field(None, description="Elasticsearch URL")
    index_name: Optional[str] = Field(None, description="Elasticsearch索引名")


class StandardCollectionDefinition(BaseModel):
    """标准集合定义"""
    base_config: VectorStoreConfig = Field(..., description="基础配置")
    collection_schema: CollectionSchema = Field(..., description="集合模式")
    index_config: IndexParameters = Field(..., description="索引配置")
    partition_config: PartitionConfig = Field(..., description="分区配置")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class DocumentMetadataSchema(BaseModel):
    """文档元数据标准模式"""
    document_id: str = Field(..., description="文档ID")
    knowledge_base_id: str = Field(..., description="知识库ID")
    chunk_id: str = Field(..., description="文档块ID")
    file_name: Optional[str] = Field(None, description="文件名")
    file_type: Optional[str] = Field(None, description="文件类型")
    file_size: Optional[int] = Field(None, description="文件大小")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    # 文本相关元数据
    chunk_index: Optional[int] = Field(None, description="块索引")
    chunk_size: Optional[int] = Field(None, description="块大小")
    original_text: Optional[str] = Field(None, description="原始文本")
    summary: Optional[str] = Field(None, description="文本摘要")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    
    # 业务相关元数据
    category: Optional[str] = Field(None, description="文档分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    priority: Optional[int] = Field(None, description="优先级")
    access_level: Optional[str] = Field(None, description="访问级别")
    
    # 自定义元数据
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")


# 预定义的标准集合模板
def get_standard_document_collection(backend_type: VectorBackendType = VectorBackendType.MILVUS) -> StandardCollectionDefinition:
    """获取标准文档集合定义"""
    if backend_type == VectorBackendType.MILVUS:
        return _get_milvus_document_collection()
    elif backend_type == VectorBackendType.PGVECTOR:
        return _get_pgvector_document_collection()
    elif backend_type == VectorBackendType.ELASTICSEARCH:
        return _get_elasticsearch_document_collection()
    else:
        raise ValueError(f"不支持的后端类型: {backend_type}")


def _get_milvus_document_collection() -> StandardCollectionDefinition:
    """获取Milvus文档集合定义"""
    fields = [
        FieldSchema(
            name="id",
            data_type=DataType.VARCHAR,
            is_primary=True,
            max_length=100,
            description="主键ID"
        ),
        FieldSchema(
            name="document_id",
            data_type=DataType.VARCHAR,
            max_length=100,
            description="文档ID"
        ),
        FieldSchema(
            name="knowledge_base_id",
            data_type=DataType.VARCHAR,
            max_length=100,
            description="知识库ID"
        ),
        FieldSchema(
            name="chunk_id",
            data_type=DataType.VARCHAR,
            max_length=100,
            description="文档块ID"
        ),
        FieldSchema(
            name="vector",
            data_type=DataType.FLOAT_VECTOR,
            dimension=1536,
            description="文档向量"
        ),
        FieldSchema(
            name="text",
            data_type=DataType.VARCHAR,
            max_length=65535,
            description="文本内容"
        ),
        FieldSchema(
            name="metadata",
            data_type=DataType.JSON,
            description="元数据信息"
        )
    ]
    
    collection_schema = CollectionSchema(
        name="document_vectors",
        description="标准文档向量集合",
        fields=fields,
        enable_dynamic_field=True
    )
    
    index_config = IndexParameters(
        index_type=IndexType.HNSW,
        metric_type=MetricType.COSINE,
        params={
            "M": 16,
            "efConstruction": 200
        }
    )
    
    base_config = VectorStoreConfig(
        backend_type=VectorBackendType.MILVUS,
        host="localhost",
        port=19530,
        collection_name="document_vectors",
        dimension=1536
    )
    
    return StandardCollectionDefinition(
        base_config=base_config,
        collection_schema=collection_schema,
        index_config=index_config,
        partition_config=PartitionConfig()
    )


def _get_pgvector_document_collection() -> StandardCollectionDefinition:
    """获取PostgreSQL+pgvector文档集合定义"""
    fields = [
        FieldSchema(
            name="id",
            data_type=DataType.UUID,
            is_primary=True,
            default_value="gen_random_uuid()",
            description="主键ID"
        ),
        FieldSchema(
            name="document_id",
            data_type=DataType.VARCHAR,
            max_length=100,
            nullable=False,
            description="文档ID"
        ),
        FieldSchema(
            name="knowledge_base_id", 
            data_type=DataType.VARCHAR,
            max_length=100,
            nullable=False,
            description="知识库ID"
        ),
        FieldSchema(
            name="chunk_id",
            data_type=DataType.VARCHAR,
            max_length=100,
            nullable=False,
            description="文档块ID"
        ),
        FieldSchema(
            name="embedding",
            data_type=DataType.VECTOR,
            dimension=1536,
            description="文档向量（pgvector类型）"
        ),
        FieldSchema(
            name="content",
            data_type=DataType.TEXT,
            description="文本内容"
        ),
        FieldSchema(
            name="metadata",
            data_type=DataType.JSONB,
            description="元数据信息"
        ),
        FieldSchema(
            name="created_at",
            data_type=DataType.TIMESTAMP,
            default_value="CURRENT_TIMESTAMP",
            description="创建时间"
        ),
        FieldSchema(
            name="updated_at",
            data_type=DataType.TIMESTAMP,
            default_value="CURRENT_TIMESTAMP",
            description="更新时间"
        )
    ]
    
    collection_schema = CollectionSchema(
        name="document_vectors",
        description="PostgreSQL+pgvector文档向量表",
        fields=fields,
        enable_dynamic_field=False
    )
    
    index_config = IndexParameters(
        index_type=IndexType.IVFFLAT,
        metric_type=MetricType.COSINE_PG,
        params={
            "lists": 100
        }
    )
    
    base_config = VectorStoreConfig(
        backend_type=VectorBackendType.PGVECTOR,
        database_url="postgresql://user:password@localhost:5432/database",
        schema_name="public",
        table_name="document_vectors",
        collection_name="document_vectors",
        dimension=1536
    )
    
    return StandardCollectionDefinition(
        base_config=base_config,
        collection_schema=collection_schema,
        index_config=index_config,
        partition_config=PartitionConfig(enabled=False)
    )


def _get_elasticsearch_document_collection() -> StandardCollectionDefinition:
    """获取Elasticsearch文档集合定义"""
    fields = [
        FieldSchema(
            name="id",
            data_type=DataType.KEYWORD,
            is_primary=True,
            description="主键ID"
        ),
        FieldSchema(
            name="document_id",
            data_type=DataType.KEYWORD,
            nullable=False,
            description="文档ID"
        ),
        FieldSchema(
            name="knowledge_base_id",
            data_type=DataType.KEYWORD,
            nullable=False,
            description="知识库ID"
        ),
        FieldSchema(
            name="chunk_id",
            data_type=DataType.KEYWORD,
            nullable=False,
            description="文档块ID"
        ),
        FieldSchema(
            name="embedding",
            data_type=DataType.DENSE_VECTOR,
            dimension=1536,
            description="文档向量（dense_vector类型）"
        ),
        FieldSchema(
            name="content",
            data_type=DataType.TEXT,
            description="文本内容"
        ),
        FieldSchema(
            name="metadata",
            data_type=DataType.OBJECT,
            description="元数据信息"
        ),
        FieldSchema(
            name="created_at",
            data_type=DataType.DATE,
            description="创建时间"
        ),
        FieldSchema(
            name="updated_at",
            data_type=DataType.DATE,
            description="更新时间"
        )
    ]
    
    collection_schema = CollectionSchema(
        name="document_vectors",
        description="Elasticsearch文档向量索引",
        fields=fields,
        enable_dynamic_field=False
    )
    
    index_config = IndexParameters(
        index_type=IndexType.DENSE_VECTOR,
        metric_type=MetricType.COSINE_ES,
        params={
            "similarity": "cosine"
        }
    )
    
    base_config = VectorStoreConfig(
        backend_type=VectorBackendType.ELASTICSEARCH,
        es_url="http://localhost:9200",
        index_name="document_vectors",
        collection_name="document_vectors",
        dimension=1536
    )
    
    return StandardCollectionDefinition(
        base_config=base_config,
        collection_schema=collection_schema,
        index_config=index_config,
        partition_config=PartitionConfig(enabled=False)
    )


def get_knowledge_base_collection(backend_type: VectorBackendType = VectorBackendType.MILVUS) -> StandardCollectionDefinition:
    """获取知识库集合定义"""
    if backend_type == VectorBackendType.MILVUS:
        return _get_milvus_knowledge_base_collection()
    elif backend_type == VectorBackendType.PGVECTOR:
        return _get_pgvector_knowledge_base_collection()
    elif backend_type == VectorBackendType.ELASTICSEARCH:
        return _get_elasticsearch_knowledge_base_collection()
    else:
        raise ValueError(f"不支持的后端类型: {backend_type}")


def _get_milvus_knowledge_base_collection() -> StandardCollectionDefinition:
    """获取Milvus知识库集合定义"""
    # 基于文档集合，但可能有不同的配置
    config = _get_milvus_document_collection()
    config.collection_schema.name = "knowledge_base_vectors"
    config.collection_schema.description = "Milvus知识库向量集合"
    config.base_config.collection_name = "knowledge_base_vectors"
    
    # 使用高性能索引配置
    config.index_config.params = {
        "M": 32,
        "efConstruction": 400
    }
    
    return config


def _get_pgvector_knowledge_base_collection() -> StandardCollectionDefinition:
    """获取PostgreSQL+pgvector知识库集合定义"""
    # 基于pgvector的知识库集合定义
    config = _get_pgvector_document_collection()
    config.collection_schema.name = "knowledge_base_vectors"
    config.collection_schema.description = "PostgreSQL+pgvector知识库向量表"
    config.base_config.table_name = "knowledge_base_vectors"
    config.base_config.collection_name = "knowledge_base_vectors"
    
    # 使用HNSW索引获得更好的性能
    config.index_config.index_type = IndexType.HNSW_PG
    config.index_config.params = {
        "m": 16,
        "ef_construction": 64
    }
    
    return config


def _get_elasticsearch_knowledge_base_collection() -> StandardCollectionDefinition:
    """获取Elasticsearch知识库集合定义"""
    config = _get_elasticsearch_document_collection()
    config.collection_schema.name = "knowledge_base_vectors"
    config.collection_schema.description = "Elasticsearch知识库向量索引"
    config.base_config.index_name = "knowledge_base_vectors"
    config.base_config.collection_name = "knowledge_base_vectors"
    
    return config


class VectorStoreInitializer(BaseModel):
    """向量存储初始化器"""
    config: StandardCollectionDefinition = Field(..., description="集合配置")
    create_if_not_exists: bool = Field(True, description="不存在时是否创建")
    drop_existing: bool = Field(False, description="是否删除已存在的集合")
    load_after_create: bool = Field(True, description="创建后是否加载集合")
    create_partitions: bool = Field(True, description="是否创建默认分区")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """获取连接参数"""
        return {
            "host": self.config.base_config.host,
            "port": self.config.base_config.port,
            "user": self.config.base_config.user,
            "password": self.config.base_config.password,
            "secure": self.config.base_config.secure,
            "timeout": self.config.base_config.timeout
        }
    
    def get_collection_params(self) -> Dict[str, Any]:
        """获取集合创建参数"""
        return {
            "name": self.config.collection_schema.name,
            "schema": self.config.collection_schema.dict(),
            "index_params": self.config.index_config.dict(),
            "partition_config": self.config.partition_config.dict()
        }


# 预定义的初始化器模板
STANDARD_TEMPLATES = {
    "document_collection": get_standard_document_collection,
    "knowledge_base_collection": get_knowledge_base_collection
} 