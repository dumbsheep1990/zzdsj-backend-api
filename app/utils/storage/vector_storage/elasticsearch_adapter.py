"""
Elasticsearch向量存储适配器
"""

from typing import List, Dict, Any, Optional, Union
import logging
import json
import uuid
from datetime import datetime
from ..core.base import VectorStorage
from ..core.exceptions import VectorStoreError, ConnectionError

try:
    from elasticsearch import Elasticsearch, AsyncElasticsearch
    from elasticsearch.helpers import bulk, async_bulk
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False

logger = logging.getLogger(__name__)


class ElasticsearchVectorStore(VectorStorage):
    """
    Elasticsearch向量存储适配器
    实现基于Elasticsearch dense_vector类型的向量存储功能
    """
    
    def __init__(self, name: str = "elasticsearch", config: Optional[Dict[str, Any]] = None):
        """
        初始化Elasticsearch向量存储
        
        参数:
            name: 存储名称
            config: 配置参数
        """
        super().__init__(name, config)
        self._client = None
        self._async_client = None
        
    async def initialize(self) -> None:
        """初始化Elasticsearch向量存储"""
        if self._initialized:
            return
        
        if not ES_AVAILABLE:
            raise VectorStoreError("Elasticsearch相关依赖库未安装")
        
        try:
            # 从配置获取连接参数
            es_url = self.get_config("es_url") or self.get_config("url", "http://localhost:9200")
            username = self.get_config("username")
            password = self.get_config("password")
            api_key = self.get_config("api_key")
            timeout = self.get_config("timeout", 30)
            
            # 构建连接配置
            es_config = {
                "hosts": [es_url],
                "timeout": timeout,
                "retry_on_timeout": True,
                "max_retries": 3
            }
            
            # 添加认证信息
            if api_key:
                es_config["api_key"] = api_key
            elif username and password:
                es_config["basic_auth"] = (username, password)
            
            # 创建客户端
            self._client = Elasticsearch(**es_config)
            self._async_client = AsyncElasticsearch(**es_config)
            
            # 测试连接
            info = self._client.info()
            self.logger.info(f"Elasticsearch连接成功: {info['version']['number']}")
            
            self._initialized = True
            self._connected = True
            
        except Exception as e:
            self.logger.error(f"Elasticsearch初始化失败: {str(e)}")
            raise ConnectionError(f"Elasticsearch连接失败: {str(e)}", endpoint=es_url)
    
    async def connect(self) -> bool:
        """建立连接"""
        if not self._initialized:
            await self.initialize()
        return self._connected
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._client:
            self._client.close()
        if self._async_client:
            await self._async_client.close()
        self._connected = False
        self.logger.info("Elasticsearch连接已断开")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._client:
                return False
            
            health = self._client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            self.logger.error(f"健康检查失败: {str(e)}")
            return False
    
    async def create_collection(self, name: str, dimension: int, **kwargs) -> bool:
        """创建向量集合（索引）"""
        try:
            if not self._connected:
                await self.connect()
            
            # 检查索引是否已存在
            if self._client.indices.exists(index=name):
                self.logger.info(f"索引 {name} 已存在")
                return True
            
            # 构建索引映射
            mapping = self._generate_index_mapping(dimension, **kwargs)
            
            # 创建索引
            self._client.indices.create(
                index=name,
                body={
                    "mappings": mapping,
                    "settings": self._get_index_settings(**kwargs)
                }
            )
            
            self.logger.info(f"成功创建Elasticsearch索引: {name}, 维度: {dimension}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建Elasticsearch索引失败: {str(e)}")
            raise VectorStoreError(f"创建索引失败: {str(e)}", collection=name)
    
    def _generate_index_mapping(self, dimension: int, **kwargs) -> Dict[str, Any]:
        """生成索引映射"""
        fields = kwargs.get("fields", [])
        
        # 基础映射
        mapping = {
            "properties": {
                "id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "knowledge_base_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": dimension,
                    "index": True,
                    "similarity": kwargs.get("similarity", "cosine")
                },
                "content": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "metadata": {"type": "object"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
            }
        }
        
        # 添加自定义字段
        for field in fields:
            field_type = self._map_field_type(field.get("data_type"))
            mapping["properties"][field["name"]] = {"type": field_type}
        
        return mapping
    
    def _map_field_type(self, data_type: str) -> str:
        """映射数据类型到Elasticsearch类型"""
        type_mapping = {
            "VARCHAR": "keyword",
            "TEXT": "text",
            "INT64": "long",
            "FLOAT": "float",
            "DOUBLE": "double",
            "BOOL": "boolean",
            "JSON": "object",
            "JSONB": "object",
            "TIMESTAMP": "date"
        }
        return type_mapping.get(data_type, "keyword")
    
    def _get_index_settings(self, **kwargs) -> Dict[str, Any]:
        """获取索引设置"""
        return {
            "number_of_shards": kwargs.get("shards", 1),
            "number_of_replicas": kwargs.get("replicas", 0),
            "refresh_interval": kwargs.get("refresh_interval", "1s")
        }
    
    async def add_vectors(self, 
                         collection: str,
                         vectors: List[List[float]], 
                         ids: Optional[List[Union[int, str]]] = None,
                         metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """添加向量"""
        try:
            if not self._connected:
                await self.connect()
            
            # 准备批量插入数据
            actions = []
            for i, vector in enumerate(vectors):
                doc_id = ids[i] if ids and i < len(ids) else str(uuid.uuid4())
                
                doc = {
                    "id": str(doc_id),
                    "embedding": vector,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                # 添加元数据
                if metadata and i < len(metadata):
                    meta = metadata[i]
                    doc.update({
                        "document_id": meta.get("document_id"),
                        "knowledge_base_id": meta.get("knowledge_base_id"),
                        "chunk_id": meta.get("chunk_id"),
                        "content": meta.get("content"),
                        "metadata": meta.get("metadata", {})
                    })
                
                action = {
                    "_index": collection,
                    "_id": doc_id,
                    "_source": doc
                }
                actions.append(action)
            
            # 批量插入
            success, failed = bulk(self._client, actions)
            
            self.logger.info(f"成功向索引 {collection} 添加 {success} 个向量")
            if failed:
                self.logger.warning(f"失败 {len(failed)} 个向量")
            
            return success > 0
            
        except Exception as e:
            self.logger.error(f"添加向量失败: {str(e)}")
            raise VectorStoreError(f"添加向量失败: {str(e)}", collection=collection)
    
    async def search_vectors(self, 
                           collection: str,
                           query_vector: List[float],
                           top_k: int = 10,
                           filter_conditions: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        try:
            if not self._connected:
                await self.connect()
            
            # 构建搜索查询
            query = {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_vector,
                    "k": top_k,
                    "num_candidates": min(top_k * 10, 1000)
                }
            }
            
            # 添加过滤条件
            if filter_conditions:
                filter_query = {"bool": {"must": []}}
                for key, value in filter_conditions.items():
                    if isinstance(value, list):
                        filter_query["bool"]["must"].append({"terms": {key: value}})
                    else:
                        filter_query["bool"]["must"].append({"term": {key: value}})
                
                query["knn"]["filter"] = filter_query
            
            # 执行搜索
            response = self._client.search(
                index=collection,
                body={"query": query},
                size=top_k
            )
            
            # 处理结果
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append({
                    "id": source.get("id", hit["_id"]),
                    "document_id": source.get("document_id"),
                    "knowledge_base_id": source.get("knowledge_base_id"),
                    "chunk_id": source.get("chunk_id"),
                    "content": source.get("content"),
                    "metadata": source.get("metadata", {}),
                    "score": hit["_score"],
                    "vector": source.get("embedding")
                })
            
            self.logger.info(f"在索引 {collection} 中搜索到 {len(results)} 个结果")
            return results
            
        except Exception as e:
            self.logger.error(f"搜索向量失败: {str(e)}")
            raise VectorStoreError(f"搜索向量失败: {str(e)}", collection=collection)
    
    async def delete_vectors(self, 
                           collection: str,
                           ids: List[Union[int, str]]) -> bool:
        """删除向量"""
        try:
            if not self._connected:
                await self.connect()
            
            # 构建删除操作
            actions = []
            for doc_id in ids:
                actions.append({
                    "_op_type": "delete",
                    "_index": collection,
                    "_id": str(doc_id)
                })
            
            # 批量删除
            success, failed = bulk(self._client, actions, ignore=[404])
            
            self.logger.info(f"从索引 {collection} 删除了 {success} 个向量")
            return success > 0
            
        except Exception as e:
            self.logger.error(f"删除向量失败: {str(e)}")
            raise VectorStoreError(f"删除向量失败: {str(e)}", collection=collection)
    
    async def collection_exists(self, name: str) -> bool:
        """检查集合（索引）是否存在"""
        try:
            if not self._connected:
                await self.connect()
            
            return self._client.indices.exists(index=name)
            
        except Exception as e:
            self.logger.error(f"检查索引存在性失败: {str(e)}")
            return False
    
    async def drop_collection(self, name: str) -> bool:
        """删除集合（索引）"""
        try:
            if not self._connected:
                await self.connect()
            
            self._client.indices.delete(index=name)
            
            self.logger.info(f"删除索引 {name} 成功")
            return True
            
        except Exception as e:
            self.logger.error(f"删除索引失败: {str(e)}")
            raise VectorStoreError(f"删除索引失败: {str(e)}", collection=name)
    
    async def get_collection_stats(self, name: str) -> Dict[str, Any]:
        """获取集合（索引）统计信息"""
        try:
            if not self._connected:
                await self.connect()
            
            # 获取索引统计信息
            stats = self._client.indices.stats(index=name)
            index_stats = stats["indices"][name]
            
            return {
                "name": name,
                "total_vectors": index_stats["total"]["docs"]["count"],
                "size": index_stats["total"]["store"]["size_in_bytes"],
                "backend": "elasticsearch"
            }
            
        except Exception as e:
            self.logger.error(f"获取索引统计信息失败: {str(e)}")
            return {"name": name, "total_vectors": 0, "backend": "elasticsearch"} 