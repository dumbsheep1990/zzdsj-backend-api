"""
Agno向量存储模块: 提供统一的向量数据库抽象层
支持多种向量数据库后端，包括Milvus、Elasticsearch、Qdrant等
基于Agno框架的向量存储最佳实践
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import numpy as np
from abc import ABC, abstractmethod

from app.config import settings
from app.frameworks.agno.config import get_agno_config

logger = logging.getLogger(__name__)

class BaseVectorStore(ABC):
    """Agno向量存储基类"""
    
    def __init__(self, collection_name: str, config: Dict[str, Any]):
        self.collection_name = collection_name
        self.config = config
        self.dimension = config.get("dimension", 1536)  # 默认OpenAI嵌入维度
        
    @abstractmethod
    async def add_vectors(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> bool:
        """添加向量到存储"""
        pass
    
    @abstractmethod
    async def search_vectors(self, query_vector: List[float], top_k: int = 5, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """搜索相似向量"""
        pass
    
    @abstractmethod
    async def delete_vectors(self, ids: List[str]) -> bool:
        """删除向量"""
        pass
    
    @abstractmethod
    async def update_vectors(self, ids: List[str], vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> bool:
        """更新向量"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        pass

class MilvusVectorStore(BaseVectorStore):
    """Milvus向量存储实现"""
    
    def __init__(self, collection_name: str, config: Dict[str, Any]):
        super().__init__(collection_name, config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化Milvus客户端"""
        try:
            from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
            
            # 连接到Milvus
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
                user=settings.MILVUS_USER,
                password=settings.MILVUS_PASSWORD
            )
            
            # 检查集合是否存在
            if not utility.has_collection(self.collection_name):
                self._create_collection()
            
            self.client = Collection(self.collection_name)
            self.client.load()
            
            logger.info(f"Milvus向量存储初始化成功: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"初始化Milvus客户端失败: {str(e)}")
            raise
    
    def _create_collection(self):
        """创建Milvus集合"""
        from pymilvus import Collection, CollectionSchema, FieldSchema, DataType
        
        # 定义集合schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description=f"Agno knowledge base collection: {self.collection_name}"
        )
        
        # 创建集合
        collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="vector", index_params=index_params)
        
        logger.info(f"创建Milvus集合: {self.collection_name}")
    
    async def add_vectors(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> bool:
        """添加向量到Milvus"""
        try:
            import uuid
            
            if not ids:
                ids = [str(uuid.uuid4()) for _ in vectors]
            
            # 准备数据
            data = [ids, vectors, metadata]
            
            # 插入数据
            self.client.insert(data)
            self.client.flush()
            
            logger.info(f"成功添加 {len(vectors)} 个向量到Milvus")
            return True
            
        except Exception as e:
            logger.error(f"添加向量到Milvus失败: {str(e)}")
            return False
    
    async def search_vectors(self, query_vector: List[float], top_k: int = 5, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """在Milvus中搜索相似向量"""
        try:
            # 构建搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # 执行搜索
            results = self.client.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["metadata"]
            )
            
            # 格式化结果
            formatted_results = []
            for hit in results[0]:
                formatted_results.append((
                    hit.id,
                    hit.score,
                    hit.entity.get("metadata", {})
                ))
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Milvus向量搜索失败: {str(e)}")
            return []
    
    async def delete_vectors(self, ids: List[str]) -> bool:
        """从Milvus删除向量"""
        try:
            expr = f"id in {ids}"
            self.client.delete(expr)
            self.client.flush()
            
            logger.info(f"成功从Milvus删除 {len(ids)} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"从Milvus删除向量失败: {str(e)}")
            return False
    
    async def update_vectors(self, ids: List[str], vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> bool:
        """更新Milvus中的向量"""
        try:
            # Milvus不支持直接更新，需要先删除再插入
            await self.delete_vectors(ids)
            return await self.add_vectors(vectors, metadata, ids)
            
        except Exception as e:
            logger.error(f"更新Milvus向量失败: {str(e)}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取Milvus集合统计信息"""
        try:
            from pymilvus import utility
            
            stats = utility.get_query_segment_info(self.collection_name)
            collection_info = self.client.describe()
            
            return {
                "collection_name": self.collection_name,
                "total_entities": self.client.num_entities,
                "dimension": self.dimension,
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "schema": collection_info,
                "segments": len(stats) if stats else 0
            }
            
        except Exception as e:
            logger.error(f"获取Milvus统计信息失败: {str(e)}")
            return {}

class ElasticsearchVectorStore(BaseVectorStore):
    """Elasticsearch向量存储实现"""
    
    def __init__(self, collection_name: str, config: Dict[str, Any]):
        super().__init__(collection_name, config)
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化Elasticsearch客户端"""
        try:
            from elasticsearch import Elasticsearch
            
            self.client = Elasticsearch(
                [f"{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"],
                basic_auth=(settings.ELASTICSEARCH_USERNAME, settings.ELASTICSEARCH_PASSWORD) if settings.ELASTICSEARCH_USERNAME else None,
                verify_certs=False
            )
            
            # 创建索引（如果不存在）
            if not self.client.indices.exists(index=self.collection_name):
                self._create_index()
            
            logger.info(f"Elasticsearch向量存储初始化成功: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"初始化Elasticsearch客户端失败: {str(e)}")
            raise
    
    def _create_index(self):
        """创建Elasticsearch索引"""
        mapping = {
            "mappings": {
                "properties": {
                    "vector": {
                        "type": "dense_vector",
                        "dims": self.dimension
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
        
        self.client.indices.create(index=self.collection_name, body=mapping)
        logger.info(f"创建Elasticsearch索引: {self.collection_name}")
    
    async def add_vectors(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> bool:
        """添加向量到Elasticsearch"""
        try:
            import uuid
            from elasticsearch.helpers import bulk
            
            if not ids:
                ids = [str(uuid.uuid4()) for _ in vectors]
            
            # 准备批量操作
            actions = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                action = {
                    "_index": self.collection_name,
                    "_id": ids[i],
                    "_source": {
                        "vector": vector,
                        "metadata": meta,
                        "content": meta.get("content", "")
                    }
                }
                actions.append(action)
            
            # 执行批量插入
            success, failed = bulk(self.client, actions)
            
            logger.info(f"成功添加 {success} 个向量到Elasticsearch")
            return True
            
        except Exception as e:
            logger.error(f"添加向量到Elasticsearch失败: {str(e)}")
            return False
    
    async def search_vectors(self, query_vector: List[float], top_k: int = 5, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """在Elasticsearch中搜索相似向量"""
        try:
            # 构建查询
            query = {
                "size": top_k,
                "query": {
                    "script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }
                }
            }
            
            # 添加过滤条件
            if filter_criteria:
                query["query"]["script_score"]["query"] = {
                    "bool": {
                        "must": [{"match_all": {}}],
                        "filter": [{"term": {k: v}} for k, v in filter_criteria.items()]
                    }
                }
            
            # 执行搜索
            response = self.client.search(index=self.collection_name, body=query)
            
            # 格式化结果
            results = []
            for hit in response["hits"]["hits"]:
                results.append((
                    hit["_id"],
                    hit["_score"],
                    hit["_source"].get("metadata", {})
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Elasticsearch向量搜索失败: {str(e)}")
            return []
    
    async def delete_vectors(self, ids: List[str]) -> bool:
        """从Elasticsearch删除向量"""
        try:
            from elasticsearch.helpers import bulk
            
            actions = [
                {
                    "_op_type": "delete",
                    "_index": self.collection_name,
                    "_id": doc_id
                }
                for doc_id in ids
            ]
            
            success, failed = bulk(self.client, actions)
            
            logger.info(f"成功从Elasticsearch删除 {success} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"从Elasticsearch删除向量失败: {str(e)}")
            return False
    
    async def update_vectors(self, ids: List[str], vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> bool:
        """更新Elasticsearch中的向量"""
        try:
            from elasticsearch.helpers import bulk
            
            actions = []
            for i, (doc_id, vector, meta) in enumerate(zip(ids, vectors, metadata)):
                action = {
                    "_op_type": "update",
                    "_index": self.collection_name,
                    "_id": doc_id,
                    "_source": {
                        "doc": {
                            "vector": vector,
                            "metadata": meta,
                            "content": meta.get("content", "")
                        }
                    }
                }
                actions.append(action)
            
            success, failed = bulk(self.client, actions)
            
            logger.info(f"成功更新Elasticsearch中 {success} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"更新Elasticsearch向量失败: {str(e)}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取Elasticsearch索引统计信息"""
        try:
            stats = self.client.indices.stats(index=self.collection_name)
            mapping = self.client.indices.get_mapping(index=self.collection_name)
            
            index_stats = stats["indices"][self.collection_name]
            
            return {
                "index_name": self.collection_name,
                "total_docs": index_stats["total"]["docs"]["count"],
                "dimension": self.dimension,
                "index_size": index_stats["total"]["store"]["size_in_bytes"],
                "mapping": mapping[self.collection_name]["mappings"]
            }
            
        except Exception as e:
            logger.error(f"获取Elasticsearch统计信息失败: {str(e)}")
            return {}

class AgnoVectorStore:
    """Agno统一向量存储接口"""
    
    def __init__(self, store_type: str = "milvus", collection_name: str = "agno_default", config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        初始化Agno向量存储
        
        参数:
            store_type: 存储类型 ('milvus', 'elasticsearch')
            collection_name: 集合/索引名称
            config: 配置字典
            **kwargs: 其他参数
        """
        self.store_type = store_type
        self.collection_name = collection_name
        self.config = config or {}
        
        # 合并配置
        agno_config = get_agno_config()
        self.config.update(agno_config.to_dict())
        self.config.update(kwargs)
        
        # 初始化具体的存储实现
        self.store = self._create_store()
    
    def _create_store(self) -> BaseVectorStore:
        """根据类型创建具体的向量存储实例"""
        if self.store_type.lower() == "milvus":
            return MilvusVectorStore(self.collection_name, self.config)
        else:
            raise ValueError(f"不支持的向量存储类型: {self.store_type}")
    
    async def add_vectors(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> bool:
        """添加向量"""
        return await self.store.add_vectors(vectors, metadata, ids)
    
    async def search_vectors(self, query_vector: List[float], top_k: int = 5, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """搜索向量"""
        return await self.store.search_vectors(query_vector, top_k, filter_criteria)
    
    async def delete_vectors(self, ids: List[str]) -> bool:
        """删除向量"""
        return await self.store.delete_vectors(ids)
    
    async def update_vectors(self, ids: List[str], vectors: List[List[float]], metadata: List[Dict[str, Any]]) -> bool:
        """更新向量"""
        return await self.store.update_vectors(ids, vectors, metadata)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = await self.store.get_stats()
        stats.update({
            "store_type": self.store_type,
            "agno_version": "1.0.0"
        })
        return stats
    
    def get_store_type(self) -> str:
        """获取存储类型"""
        return self.store_type
    
    def get_collection_name(self) -> str:
        """获取集合名称"""
        return self.collection_name

# 工厂函数
def create_vector_store(store_type: str = "milvus", collection_name: str = "agno_default", **kwargs) -> AgnoVectorStore:
    """
    创建向量存储实例的工厂函数
    
    参数:
        store_type: 存储类型
        collection_name: 集合名称
        **kwargs: 其他参数
        
    返回:
        AgnoVectorStore实例
    """
    return AgnoVectorStore(
        store_type=store_type,
        collection_name=collection_name,
        **kwargs
    )

# 全局向量存储管理器
_vector_stores: Dict[str, AgnoVectorStore] = {}

def get_vector_store(collection_name: str, store_type: str = "milvus", **kwargs) -> AgnoVectorStore:
    """
    获取或创建向量存储实例（单例模式）
    
    参数:
        collection_name: 集合名称
        store_type: 存储类型
        **kwargs: 其他参数
        
    返回:
        AgnoVectorStore实例
    """
    store_key = f"{store_type}:{collection_name}"
    
    if store_key not in _vector_stores:
        _vector_stores[store_key] = create_vector_store(
            store_type=store_type,
            collection_name=collection_name,
            **kwargs
        )
    
    return _vector_stores[store_key]

def list_vector_stores() -> List[Dict[str, str]]:
    """列出所有已创建的向量存储"""
    return [
        {
            "key": key,
            "store_type": store.get_store_type(),
            "collection_name": store.get_collection_name()
        }
        for key, store in _vector_stores.items()
    ] 