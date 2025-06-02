"""
向量数据库标准初始化器
基于配置模式创建和管理向量数据库集合
支持多种向量数据库后端：Milvus、PostgreSQL+pgvector、Elasticsearch等
"""

import logging
from typing import Dict, List, Any, Optional, Union

from app.schemas.vector_store import (
    StandardCollectionDefinition,
    VectorStoreInitializer,
    VectorBackendType,
    DataType,
    IndexType,
    MetricType,
    STANDARD_TEMPLATES
)

logger = logging.getLogger(__name__)


class StandardVectorStoreInitializer:
    """标准向量存储初始化器"""
    
    def __init__(self, initializer_config: VectorStoreInitializer):
        """
        初始化向量存储初始化器
        
        参数:
            initializer_config: 初始化器配置
        """
        self.config = initializer_config
        self.backend_type = initializer_config.config.base_config.backend_type
        self.connection_alias = initializer_config.config.base_config.connection_alias
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 根据后端类型初始化相应的客户端
        self._backend_client = None
        
    def initialize(self) -> bool:
        """
        执行向量存储初始化
        
        返回:
            初始化是否成功
        """
        try:
            self.logger.info(f"开始初始化{self.backend_type}向量存储...")
            
            # 根据后端类型选择初始化方法
            if self.backend_type == VectorBackendType.MILVUS:
                return self._initialize_milvus()
            elif self.backend_type == VectorBackendType.PGVECTOR:
                return self._initialize_pgvector()
            elif self.backend_type == VectorBackendType.ELASTICSEARCH:
                return self._initialize_elasticsearch()
            else:
                raise ValueError(f"不支持的向量存储后端类型: {self.backend_type}")
                
        except Exception as e:
            self.logger.error(f"向量存储初始化失败: {str(e)}")
            return False
    
    def _initialize_milvus(self) -> bool:
        """初始化Milvus向量存储"""
        try:
            from pymilvus import (
                connections, 
                utility,
                FieldSchema as MilvusFieldSchema, 
                CollectionSchema as MilvusCollectionSchema, 
                DataType as MilvusDataType,
                Collection
            )
            
            # 1. 建立连接
            connection_params = self.config.get_connection_params()
            connections.connect(
                alias=self.connection_alias,
                host=connection_params["host"],
                port=connection_params["port"],
                user=connection_params.get("user"),
                password=connection_params.get("password"),
                secure=connection_params.get("secure", False),
                timeout=connection_params.get("timeout", 10)
            )
            
            self.logger.info(f"Milvus连接成功: {connection_params['host']}:{connection_params['port']}")
            
            # 2. 检查并创建集合
            collection_name = self.config.config.collection_schema.name
            
            if utility.has_collection(collection_name, using=self.connection_alias):
                if self.config.drop_existing:
                    utility.drop_collection(collection_name, using=self.connection_alias)
                    self.logger.info(f"已删除现有集合: {collection_name}")
                else:
                    self.logger.info(f"集合 {collection_name} 已存在，跳过创建")
                    return True
            
            # 3. 创建集合
            success = self._create_milvus_collection()
            if not success:
                return False
            
            # 4. 创建索引
            success = self._create_milvus_index()
            if not success:
                return False
            
            # 5. 创建分区（如果启用）
            if self.config.create_partitions and self.config.config.partition_config.enabled:
                success = self._create_milvus_partitions()
                if not success:
                    return False
            
            # 6. 加载集合（如果配置要求）
            if self.config.load_after_create:
                collection = Collection(collection_name, using=self.connection_alias)
                collection.load()
                self.logger.info(f"集合 {collection_name} 已加载到内存")
            
            self.logger.info(f"Milvus向量存储初始化完成: {collection_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Milvus初始化失败: {str(e)}")
            return False
    
    def _initialize_pgvector(self) -> bool:
        """初始化PostgreSQL+pgvector向量存储"""
        try:
            from .pgvector_adapter import PgVectorStore
            
            # 1. 创建pgvector客户端
            config_dict = self.config.config.base_config.dict()
            pgvector_store = PgVectorStore("standard_init", config_dict)
            
            # 2. 初始化连接
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 连接到数据库
                success = loop.run_until_complete(pgvector_store.connect())
                if not success:
                    self.logger.error("PostgreSQL连接失败")
                    return False
                
                self.logger.info("PostgreSQL+pgvector连接成功")
                
                # 3. 检查并创建表
                table_name = self.config.config.collection_schema.name
                
                exists = loop.run_until_complete(pgvector_store.collection_exists(table_name))
                if exists:
                    if self.config.drop_existing:
                        loop.run_until_complete(pgvector_store.drop_collection(table_name))
                        self.logger.info(f"已删除现有表: {table_name}")
                    else:
                        self.logger.info(f"表 {table_name} 已存在，跳过创建")
                        return True
                
                # 4. 创建表和索引
                success = self._create_pgvector_table(pgvector_store, loop)
                if not success:
                    return False
                
                self.logger.info(f"PostgreSQL+pgvector向量存储初始化完成: {table_name}")
                return True
                
            finally:
                loop.run_until_complete(pgvector_store.disconnect())
                loop.close()
                
        except Exception as e:
            self.logger.error(f"PostgreSQL+pgvector初始化失败: {str(e)}")
            return False
    
    def _initialize_elasticsearch(self) -> bool:
        """初始化Elasticsearch向量存储"""
        try:
            from .elasticsearch_adapter import ElasticsearchVectorStore
            
            # 1. 创建Elasticsearch客户端
            config_dict = self.config.config.base_config.dict()
            es_store = ElasticsearchVectorStore("standard_init", config_dict)
            
            # 2. 初始化连接
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 连接到Elasticsearch
                success = loop.run_until_complete(es_store.connect())
                if not success:
                    self.logger.error("Elasticsearch连接失败")
                    return False
                
                self.logger.info("Elasticsearch连接成功")
                
                # 3. 检查并创建索引
                index_name = self.config.config.collection_schema.name
                
                exists = loop.run_until_complete(es_store.collection_exists(index_name))
                if exists:
                    if self.config.drop_existing:
                        loop.run_until_complete(es_store.drop_collection(index_name))
                        self.logger.info(f"已删除现有索引: {index_name}")
                    else:
                        self.logger.info(f"索引 {index_name} 已存在，跳过创建")
                        return True
                
                # 4. 创建索引
                success = self._create_elasticsearch_index(es_store, loop)
                if not success:
                    return False
                
                self.logger.info(f"Elasticsearch向量存储初始化完成: {index_name}")
                return True
                
            finally:
                loop.run_until_complete(es_store.disconnect())
                loop.close()
                
        except Exception as e:
            self.logger.error(f"Elasticsearch初始化失败: {str(e)}")
            return False
    
    def _create_milvus_collection(self) -> bool:
        """创建Milvus集合"""
        try:
            from pymilvus import (
                FieldSchema as MilvusFieldSchema, 
                CollectionSchema as MilvusCollectionSchema, 
                DataType as MilvusDataType,
                Collection
            )
            
            # 转换字段定义
            fields = []
            for field in self.config.config.collection_schema.fields:
                milvus_field = MilvusFieldSchema(
                    name=field.name,
                    dtype=self._map_milvus_data_type(field.data_type),
                    is_primary=field.is_primary,
                    auto_id=field.auto_id,
                    max_length=field.max_length,
                    dim=field.dimension,
                    description=field.description
                )
                fields.append(milvus_field)
            
            # 创建集合模式
            schema = MilvusCollectionSchema(
                fields=fields,
                description=self.config.config.collection_schema.description,
                enable_dynamic_field=self.config.config.collection_schema.enable_dynamic_field
            )
            
            # 创建集合
            collection = Collection(
                name=self.config.config.collection_schema.name,
                schema=schema,
                using=self.connection_alias
            )
            
            self.logger.info(f"Milvus集合创建成功: {collection.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Milvus集合创建失败: {str(e)}")
            return False
    
    def _create_pgvector_table(self, pgvector_store, loop) -> bool:
        """创建PostgreSQL+pgvector表"""
        try:
            # 准备创建参数
            table_name = self.config.config.collection_schema.name
            
            # 获取向量字段的维度
            vector_dimension = 1536  # 默认维度
            for field in self.config.config.collection_schema.fields:
                if field.data_type in [DataType.FLOAT_VECTOR, DataType.VECTOR]:
                    vector_dimension = field.dimension or 1536
                    break
            
            # 准备字段信息
            fields_info = []
            for field in self.config.config.collection_schema.fields:
                field_info = {
                    "name": field.name,
                    "data_type": field.data_type.value,
                    "nullable": field.nullable,
                    "default_value": field.default_value
                }
                fields_info.append(field_info)
            
            # 准备索引参数
            index_params = {
                "index_type": self.config.config.index_config.index_type.value.lower(),
                "metric_type": self.config.config.index_config.metric_type.value,
                "index_params": self.config.config.index_config.params
            }
            
            # 创建表
            success = loop.run_until_complete(
                pgvector_store.create_collection(
                    name=table_name,
                    dimension=vector_dimension,
                    fields=fields_info,
                    **index_params
                )
            )
            
            if success:
                self.logger.info(f"PostgreSQL+pgvector表创建成功: {table_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"PostgreSQL+pgvector表创建失败: {str(e)}")
            return False
    
    def _create_milvus_index(self) -> bool:
        """创建Milvus索引"""
        try:
            from pymilvus import Collection
            
            collection = Collection(
                self.config.config.collection_schema.name,
                using=self.connection_alias
            )
            
            # 查找向量字段
            vector_field = None
            for field in self.config.config.collection_schema.fields:
                if field.data_type == DataType.FLOAT_VECTOR:
                    vector_field = field.name
                    break
            
            if not vector_field:
                self.logger.warning("未找到向量字段，跳过索引创建")
                return True
            
            # 创建索引参数
            index_params = {
                "index_type": self.config.config.index_config.index_type.value,
                "metric_type": self.config.config.index_config.metric_type.value,
                "params": self.config.config.index_config.params
            }
            
            # 创建索引
            collection.create_index(
                field_name=vector_field,
                index_params=index_params
            )
            
            self.logger.info(f"Milvus索引创建成功: {vector_field}")
            return True
            
        except Exception as e:
            self.logger.error(f"Milvus索引创建失败: {str(e)}")
            return False
    
    def _create_milvus_partitions(self) -> bool:
        """创建Milvus分区"""
        try:
            from pymilvus import Collection
            
            collection = Collection(
                self.config.config.collection_schema.name,
                using=self.connection_alias
            )
            
            # 创建默认分区
            for partition_name in self.config.config.partition_config.default_partitions:
                if partition_name != "_default":  # 默认分区已存在
                    collection.create_partition(partition_name)
                    self.logger.info(f"Milvus分区创建成功: {partition_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Milvus分区创建失败: {str(e)}")
            return False
    
    def _map_milvus_data_type(self, data_type: DataType):
        """映射数据类型到Milvus类型"""
        from pymilvus import DataType as MilvusDataType
        
        type_mapping = {
            DataType.INT64: MilvusDataType.INT64,
            DataType.VARCHAR: MilvusDataType.VARCHAR,
            DataType.FLOAT_VECTOR: MilvusDataType.FLOAT_VECTOR,
            DataType.JSON: MilvusDataType.JSON,
            DataType.BOOL: MilvusDataType.BOOL,
            DataType.FLOAT: MilvusDataType.FLOAT,
            DataType.DOUBLE: MilvusDataType.DOUBLE
        }
        
        if data_type not in type_mapping:
            raise ValueError(f"不支持的Milvus数据类型: {data_type}")
        
        return type_mapping[data_type]

    def _create_elasticsearch_index(self, es_store, loop) -> bool:
        """创建Elasticsearch索引"""
        try:
            # 准备创建参数
            index_name = self.config.config.collection_schema.name
            
            # 获取向量字段的维度
            vector_dimension = 1536  # 默认维度
            for field in self.config.config.collection_schema.fields:
                if field.data_type in [DataType.DENSE_VECTOR, DataType.FLOAT_VECTOR]:
                    vector_dimension = field.dimension or 1536
                    break
            
            # 准备字段信息
            fields_info = []
            for field in self.config.config.collection_schema.fields:
                field_info = {
                    "name": field.name,
                    "data_type": field.data_type.value,
                    "nullable": field.nullable
                }
                fields_info.append(field_info)
            
            # 准备索引参数
            index_params = {
                "similarity": self.config.config.index_config.params.get("similarity", "cosine"),
                "fields": fields_info
            }
            
            # 创建索引
            success = loop.run_until_complete(
                es_store.create_collection(
                    name=index_name,
                    dimension=vector_dimension,
                    **index_params
                )
            )
            
            if success:
                self.logger.info(f"Elasticsearch索引创建成功: {index_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Elasticsearch索引创建失败: {str(e)}")
            return False


class VectorStoreFactory:
    """向量存储工厂类"""
    
    @staticmethod
    def create_from_template(template_name: str, backend_type: VectorBackendType = None, **kwargs) -> StandardVectorStoreInitializer:
        """
        从模板创建初始化器
        
        参数:
            template_name: 模板名称
            backend_type: 后端类型（可选，用于覆盖模板默认设置）
            **kwargs: 配置覆盖参数
            
        返回:
            初始化器实例
        """
        if template_name not in STANDARD_TEMPLATES:
            raise ValueError(f"未知的模板: {template_name}")
        
        # 确定后端类型
        final_backend_type = backend_type or kwargs.get("backend_type", VectorBackendType.MILVUS)
        
        # 获取标准配置
        if template_name == "document_collection":
            from app.schemas.vector_store import get_standard_document_collection
            standard_config = get_standard_document_collection(final_backend_type)
        elif template_name == "knowledge_base_collection":
            from app.schemas.vector_store import get_knowledge_base_collection
            standard_config = get_knowledge_base_collection(final_backend_type)
        else:
            # 使用旧的模板系统
            standard_config = STANDARD_TEMPLATES[template_name]()
        
        # 应用覆盖参数
        if kwargs:
            # 更新基础配置
            if "host" in kwargs:
                standard_config.base_config.host = kwargs["host"]
            if "port" in kwargs:
                standard_config.base_config.port = kwargs["port"]
            if "database_url" in kwargs:
                standard_config.base_config.database_url = kwargs["database_url"]
            if "collection_name" in kwargs:
                standard_config.collection_schema.name = kwargs["collection_name"]
            if "table_name" in kwargs:
                standard_config.base_config.table_name = kwargs["table_name"]
            if "dimension" in kwargs:
                # 更新向量字段的维度
                for field in standard_config.collection_schema.fields:
                    if field.data_type in [DataType.FLOAT_VECTOR, DataType.VECTOR]:
                        field.dimension = kwargs["dimension"]
        
        # 创建初始化器配置
        initializer_config = VectorStoreInitializer(config=standard_config)
        
        return StandardVectorStoreInitializer(initializer_config)
    
    @staticmethod
    def create_from_config(config: StandardCollectionDefinition) -> StandardVectorStoreInitializer:
        """
        从配置创建初始化器
        
        参数:
            config: 集合配置
            
        返回:
            初始化器实例
        """
        initializer_config = VectorStoreInitializer(config=config)
        return StandardVectorStoreInitializer(initializer_config)


# 便捷函数
def init_standard_document_collection(host: str = "localhost", 
                                     port: int = 19530,
                                     collection_name: str = "document_vectors",
                                     dimension: int = 1536,
                                     backend_type: VectorBackendType = VectorBackendType.MILVUS,
                                     **kwargs) -> bool:
    """
    初始化标准文档集合
    
    参数:
        host: 主机地址
        port: 端口
        collection_name: 集合名称
        dimension: 向量维度
        backend_type: 后端类型
        **kwargs: 其他配置参数
        
    返回:
        初始化是否成功
    """
    initializer = VectorStoreFactory.create_from_template(
        "document_collection",
        backend_type=backend_type,
        host=host,
        port=port,
        collection_name=collection_name,
        dimension=dimension,
        **kwargs
    )
    
    return initializer.initialize()


def init_pgvector_document_collection(database_url: str,
                                     table_name: str = "document_vectors",
                                     dimension: int = 1536) -> bool:
    """
    初始化PostgreSQL+pgvector文档集合
    
    参数:
        database_url: PostgreSQL数据库URL
        table_name: 表名称
        dimension: 向量维度
        
    返回:
        初始化是否成功
    """
    initializer = VectorStoreFactory.create_from_template(
        "document_collection",
        backend_type=VectorBackendType.PGVECTOR,
        database_url=database_url,
        table_name=table_name,
        collection_name=table_name,  # 对于pgvector，collection_name和table_name是同一个
        dimension=dimension
    )
    
    return initializer.initialize()


def init_knowledge_base_collection(host: str = "localhost",
                                  port: int = 19530,
                                  collection_name: str = "knowledge_base_vectors",
                                  dimension: int = 1536,
                                  backend_type: VectorBackendType = VectorBackendType.MILVUS,
                                  **kwargs) -> bool:
    """
    初始化知识库集合
    
    参数:
        host: 主机地址
        port: 端口
        collection_name: 集合名称
        dimension: 向量维度
        backend_type: 后端类型
        **kwargs: 其他配置参数
        
    返回:
        初始化是否成功
    """
    initializer = VectorStoreFactory.create_from_template(
        "knowledge_base_collection",
        backend_type=backend_type,
        host=host,
        port=port,
        collection_name=collection_name,
        dimension=dimension,
        **kwargs
    )
    
    return initializer.initialize()


def init_elasticsearch_document_collection(es_url: str = "http://localhost:9200",
                                          index_name: str = "document_vectors", 
                                          dimension: int = 1536,
                                          **kwargs) -> bool:
    """
    初始化Elasticsearch文档集合
    
    参数:
        es_url: Elasticsearch URL
        index_name: 索引名称
        dimension: 向量维度
        **kwargs: 其他配置参数
        
    返回:
        初始化是否成功
    """
    initializer = VectorStoreFactory.create_from_template(
        "document_collection",
        backend_type=VectorBackendType.ELASTICSEARCH,
        es_url=es_url,
        index_name=index_name,
        collection_name=index_name,
        dimension=dimension,
        **kwargs
    )
    
    return initializer.initialize()


def init_elasticsearch_knowledge_base_collection(es_url: str = "http://localhost:9200",
                                                index_name: str = "knowledge_base_vectors",
                                                dimension: int = 1536,
                                                **kwargs) -> bool:
    """
    初始化Elasticsearch知识库集合
    
    参数:
        es_url: Elasticsearch URL
        index_name: 索引名称
        dimension: 向量维度
        **kwargs: 其他配置参数
        
    返回:
        初始化是否成功
    """
    initializer = VectorStoreFactory.create_from_template(
        "knowledge_base_collection",
        backend_type=VectorBackendType.ELASTICSEARCH,
        es_url=es_url,
        index_name=index_name,
        collection_name=index_name,
        dimension=dimension,
        **kwargs
    )
    
    return initializer.initialize() 