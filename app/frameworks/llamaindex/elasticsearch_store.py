"""
LlamaIndex与Elasticsearch集成模块
提供ES索引管理、存储和检索功能
"""

from typing import Dict, List, Optional, Any, Union, Sequence, Set, Tuple
import json
import logging
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError

from llama_index.core.schema import Document, TextNode, BaseNode
from llama_index.core.vector_stores.types import VectorStore, VectorStoreQuery
from llama_index.core.vector_stores.utils import node_to_metadata_dict
from llama_index.core.indices.query.schema import QueryBundle
from app.config import settings

logger = logging.getLogger(__name__)

class ElasticsearchStore(VectorStore):
    """Elasticsearch向量存储实现，支持混合检索"""
    
    def __init__(
        self,
        index_name: str = "document_index",
        es_url: Optional[str] = None,
        es_user: Optional[str] = None,
        es_password: Optional[str] = None,
        es_cloud_id: Optional[str] = None,
        es_api_key: Optional[str] = None,
        vector_field: str = "vector_embedding",
        text_field: str = "content",
        metadata_field: str = "metadata",
        distance_strategy: str = "COSINE",
        bulk_size: int = 500,
        embedding_dimension: int = 1536,
        es_client: Optional[Elasticsearch] = None,
    ):
        """
        初始化Elasticsearch存储
        
        参数:
            index_name: ES索引名称
            es_url: ES服务器URL，如 http://localhost:9200
            es_user: ES用户名
            es_password: ES密码
            es_cloud_id: ES云ID (Elastic Cloud)
            es_api_key: ES API密钥
            vector_field: 存储向量的字段名
            text_field: 存储文本的字段名
            metadata_field: 存储元数据的字段名
            distance_strategy: 距离计算策略，可选：COSINE, DOT_PRODUCT, EUCLIDEAN
            bulk_size: 批量操作大小
            embedding_dimension: 嵌入维度
            es_client: 可选的ES客户端实例
        """
        self._index_name = index_name
        self._vector_field = vector_field
        self._text_field = text_field
        self._metadata_field = metadata_field
        self._distance_strategy = distance_strategy
        self._bulk_size = bulk_size
        self._embedding_dimension = embedding_dimension
        
        if es_client is not None:
            self._client = es_client
        else:
            # 使用配置中的ES连接信息
            es_url = es_url or settings.ELASTICSEARCH_URL
            es_user = es_user or settings.ELASTICSEARCH_USERNAME
            es_password = es_password or settings.ELASTICSEARCH_PASSWORD
            es_cloud_id = es_cloud_id or settings.ELASTICSEARCH_CLOUD_ID
            es_api_key = es_api_key or settings.ELASTICSEARCH_API_KEY
            
            # 构建ES客户端
            if es_cloud_id:
                self._client = Elasticsearch(
                    cloud_id=es_cloud_id, 
                    api_key=es_api_key if es_api_key else None,
                    basic_auth=(es_user, es_password) if es_user and es_password else None
                )
            else:
                self._client = Elasticsearch(
                    es_url,
                    basic_auth=(es_user, es_password) if es_user and es_password else None,
                    api_key=es_api_key if es_api_key else None
                )
        
        # 初始化索引
        self._initialize_index()
    
    def _initialize_index(self) -> None:
        """初始化Elasticsearch索引，如果不存在则创建"""
        try:
            index_exists = self._client.indices.exists(index=self._index_name)
            
            if not index_exists:
                logger.info(f"创建Elasticsearch索引: {self._index_name}")
                
                # 定义索引映射
                index_settings = {
                    "settings": {
                        "analysis": {
                            "analyzer": {
                                "default": {
                                    "type": "standard"  # 也可使用ik_smart等中文分词器
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            self._vector_field: {
                                "type": "dense_vector",
                                "dims": self._embedding_dimension,
                                "index": True,
                                "similarity": self._get_similarity_metric()
                            },
                            self._text_field: {
                                "type": "text",
                                "analyzer": "default"
                            },
                            self._metadata_field: {
                                "type": "object",
                                "enabled": True
                            },
                            "node_id": {"type": "keyword"},
                            "document_id": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "updated_at": {"type": "date"}
                        }
                    }
                }
                
                # 创建索引
                self._client.indices.create(
                    index=self._index_name,
                    body=index_settings
                )
                logger.info(f"Elasticsearch索引 {self._index_name} 创建成功")
            else:
                logger.info(f"Elasticsearch索引 {self._index_name} 已存在")
        
        except Exception as e:
            logger.error(f"初始化Elasticsearch索引时出错: {str(e)}")
            raise
    
    def _get_similarity_metric(self) -> str:
        """根据距离策略返回ES相似度度量"""
        if self._distance_strategy == "COSINE":
            return "cosine"
        elif self._distance_strategy == "DOT_PRODUCT":
            return "dot_product"
        elif self._distance_strategy == "EUCLIDEAN":
            return "l2_norm"
        else:
            return "cosine"
    
    def add(
        self,
        nodes: List[BaseNode],
        **add_kwargs: Any,
    ) -> List[str]:
        """
        添加节点到Elasticsearch
        
        参数:
            nodes: 要添加的节点列表
            **add_kwargs: 额外参数
            
        返回:
            添加的节点ID列表
        """
        if not nodes:
            return []
        
        node_ids = []
        actions = []
        
        # 准备批量操作
        for node in nodes:
            node_id = node.node_id
            node_ids.append(node_id)
            
            # 提取节点信息
            metadata = node_to_metadata_dict(node)
            embedding = node.embedding
            
            # 构建ES文档
            doc = {
                "_index": self._index_name,
                "_id": node_id,
                "_source": {
                    "node_id": node_id,
                    "document_id": node.ref_doc_id if hasattr(node, 'ref_doc_id') else None,
                    self._text_field: node.get_content(),
                    self._metadata_field: metadata,
                }
            }
            
            # 添加向量嵌入
            if embedding is not None:
                doc["_source"][self._vector_field] = embedding
            
            actions.append(doc)
        
        # 批量添加到ES
        if actions:
            helpers.bulk(self._client, actions)
        
        return node_ids
    
    def delete(self, node_id: str, **delete_kwargs: Any) -> None:
        """
        从Elasticsearch删除节点
        
        参数:
            node_id: 要删除的节点ID
            **delete_kwargs: 额外参数
        """
        try:
            self._client.delete(
                index=self._index_name,
                id=node_id
            )
        except NotFoundError:
            logger.warning(f"尝试删除不存在的节点: {node_id}")
        except Exception as e:
            logger.error(f"删除节点 {node_id} 时出错: {str(e)}")
            raise
    
    def query(
        self,
        query: VectorStoreQuery,
        **kwargs: Any,
    ) -> List[Tuple[BaseNode, float]]:
        """
        查询Elasticsearch
        
        参数:
            query: 向量存储查询对象
            **kwargs: 额外参数
            
        返回:
            (节点, 分数)元组的列表
        """
        query_embedding = query.query_embedding
        similarity_top_k = query.similarity_top_k or 10
        filters = query.filters or {}
        
        # 如果没有嵌入向量，则使用BM25全文搜索
        if query_embedding is None and query.query_str:
            return self._text_search(
                query_text=query.query_str,
                top_k=similarity_top_k,
                filters=filters
            )
        
        # 否则执行向量搜索
        return self._vector_search(
            query_embedding=query_embedding,
            top_k=similarity_top_k,
            filters=filters
        )
    
    def _text_search(
        self,
        query_text: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[BaseNode, float]]:
        """
        执行BM25全文搜索
        
        参数:
            query_text: 查询文本
            top_k: 返回结果数量
            filters: 可选过滤条件
            
        返回:
            (节点, 分数)元组的列表
        """
        must_conditions = [
            {"match": {self._text_field: {"query": query_text}}}
        ]
        
        # 处理过滤条件
        if filters:
            for key, value in filters.items():
                filter_key = f"{self._metadata_field}.{key}"
                
                if isinstance(value, list):
                    terms_query = {"terms": {filter_key: value}}
                    must_conditions.append(terms_query)
                else:
                    term_query = {"term": {filter_key: value}}
                    must_conditions.append(term_query)
        
        # 构建查询
        search_query = {
            "query": {
                "bool": {
                    "must": must_conditions
                }
            },
            "size": top_k
        }
        
        # 执行搜索
        response = self._client.search(
            index=self._index_name,
            body=search_query
        )
        
        return self._parse_response(response)
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[BaseNode, float]]:
        """
        执行向量相似度搜索
        
        参数:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filters: 可选过滤条件
            
        返回:
            (节点, 分数)元组的列表
        """
        # 构建kNN查询
        knn_query = {
            "field": self._vector_field,
            "query_vector": query_embedding,
            "k": top_k,
            "num_candidates": top_k * 2
        }
        
        search_query = {
            "knn": knn_query,
            "size": top_k
        }
        
        # 添加过滤条件
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                filter_key = f"{self._metadata_field}.{key}"
                
                if isinstance(value, list):
                    filter_clauses.append({"terms": {filter_key: value}})
                else:
                    filter_clauses.append({"term": {filter_key: value}})
            
            if filter_clauses:
                search_query["query"] = {
                    "bool": {"filter": filter_clauses}
                }
        
        # 执行搜索
        response = self._client.search(
            index=self._index_name,
            body=search_query
        )
        
        return self._parse_response(response)
    
    def hybrid_search(
        self,
        query_str: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        text_weight: float = 0.5
    ) -> List[Tuple[BaseNode, float]]:
        """
        执行混合搜索（同时使用BM25和向量搜索）
        
        参数:
            query_str: 查询文本
            query_embedding: 查询向量
            top_k: 返回结果数量
            filters: 可选过滤条件
            text_weight: BM25权重 (0-1 之间)
            
        返回:
            (节点, 分数)元组的列表
        """
        vector_weight = 1.0 - text_weight
        
        # 构建混合查询
        must_conditions = []
        
        # 处理过滤条件
        if filters:
            for key, value in filters.items():
                filter_key = f"{self._metadata_field}.{key}"
                
                if isinstance(value, list):
                    must_conditions.append({"terms": {filter_key: value}})
                else:
                    must_conditions.append({"term": {filter_key: value}})
        
        # 构建查询
        search_query = {
            "query": {
                "script_score": {
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {self._text_field: {"query": query_str}}}
                            ] + must_conditions
                        }
                    },
                    "script": {
                        "source": f"cosineSimilarity(params.query_vector, '{self._vector_field}') * {vector_weight} + _score * {text_weight}",
                        "params": {"query_vector": query_embedding}
                    }
                }
            },
            "size": top_k
        }
        
        # 执行搜索
        response = self._client.search(
            index=self._index_name,
            body=search_query
        )
        
        return self._parse_response(response)
    
    def _parse_response(self, response: Dict[str, Any]) -> List[Tuple[BaseNode, float]]:
        """
        解析ES响应，返回节点和分数
        
        参数:
            response: ES响应
            
        返回:
            (节点, 分数)元组的列表
        """
        results = []
        hits = response.get("hits", {}).get("hits", [])
        
        for hit in hits:
            # 提取文档信息
            source = hit.get("_source", {})
            node_id = source.get("node_id")
            text = source.get(self._text_field, "")
            metadata = source.get(self._metadata_field, {})
            score = hit.get("_score", 0.0)
            
            # 创建节点
            node = TextNode(
                text=text,
                metadata=metadata,
                id_=node_id,
            )
            
            # 可选：如果索引中存储了嵌入向量
            vector_embedding = source.get(self._vector_field)
            if vector_embedding:
                node.embedding = vector_embedding
            
            results.append((node, score))
        
        return results
    
    def update_index_settings(self, new_settings: Dict[str, Any]) -> None:
        """
        更新索引设置
        
        参数:
            new_settings: 新的索引设置
        """
        try:
            # 先关闭索引
            self._client.indices.close(index=self._index_name)
            
            # 更新设置
            self._client.indices.put_settings(
                index=self._index_name,
                body=new_settings
            )
            
            # 重新打开索引
            self._client.indices.open(index=self._index_name)
            
            logger.info(f"已更新索引 {self._index_name} 的设置")
            
        except Exception as e:
            logger.error(f"更新索引设置时出错: {str(e)}")
            # 确保索引被重新打开
            try:
                self._client.indices.open(index=self._index_name)
            except:
                pass
            raise
    
    def delete_index(self) -> None:
        """删除整个索引"""
        try:
            self._client.indices.delete(index=self._index_name)
            logger.info(f"已删除索引 {self._index_name}")
        except Exception as e:
            logger.error(f"删除索引时出错: {str(e)}")
            raise

# 全局ES存储实例
_es_store_instance = None

def get_elasticsearch_store(
    index_name: str = None,
    recreate_index: bool = False
) -> ElasticsearchStore:
    """
    获取或创建Elasticsearch存储实例
    
    参数:
        index_name: 可选的索引名称
        recreate_index: 是否重新创建索引
        
    返回:
        ElasticsearchStore实例
    """
    global _es_store_instance
    
    # 获取默认索引名称
    default_index = settings.ELASTICSEARCH_INDEX or "document_index"
    index_name = index_name or default_index
    
    # 如果已存在实例且不需要重建索引，则直接返回
    if _es_store_instance is not None and not recreate_index:
        if _es_store_instance._index_name == index_name:
            return _es_store_instance
    
    # 如果需要重建索引，且实例已存在
    if recreate_index and _es_store_instance is not None:
        try:
            _es_store_instance.delete_index()
        except:
            pass
    
    # 创建新实例
    _es_store_instance = ElasticsearchStore(
        index_name=index_name,
        embedding_dimension=settings.EMBEDDING_DIMENSION or 1536
    )
    
    return _es_store_instance
