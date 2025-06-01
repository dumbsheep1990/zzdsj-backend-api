"""
Elasticsearch管理模块：实现基于知识库的索引、别名和路由管理
支持高效的知识库隔离与混合检索
"""

import logging
from typing import Dict, List, Optional, Any, Union
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import json

from app.config import settings

logger = logging.getLogger(__name__)

class ElasticsearchManager:
    """Elasticsearch管理类，提供索引别名和路由支持"""
    
    def __init__(
        self,
        es_url: Optional[str] = None,
        es_user: Optional[str] = None,
        es_password: Optional[str] = None,
        es_cloud_id: Optional[str] = None,
        es_api_key: Optional[str] = None,
        main_index: str = "document_index"
    ):
        """
        初始化Elasticsearch管理器
        
        参数:
            es_url: ES服务器URL，如 http://localhost:9200
            es_user: ES用户名
            es_password: ES密码
            es_cloud_id: ES云ID (Elastic Cloud)
            es_api_key: ES API密钥
            main_index: 主索引名称
        """
        # 使用配置中的ES连接信息
        self.es_url = es_url or settings.ELASTICSEARCH_URL
        self.es_user = es_user or settings.ELASTICSEARCH_USERNAME
        self.es_password = es_password or settings.ELASTICSEARCH_PASSWORD
        self.es_cloud_id = es_cloud_id or settings.ELASTICSEARCH_CLOUD_ID
        self.es_api_key = es_api_key or settings.ELASTICSEARCH_API_KEY
        self.main_index = main_index
        
        # 构建ES客户端
        if self.es_cloud_id:
            self._client = Elasticsearch(
                cloud_id=self.es_cloud_id, 
                api_key=self.es_api_key if self.es_api_key else None,
                basic_auth=(self.es_user, self.es_password) if self.es_user and self.es_password else None
            )
        else:
            self._client = Elasticsearch(
                self.es_url,
                basic_auth=(self.es_user, self.es_password) if self.es_user and self.es_password else None,
                api_key=self.es_api_key if self.es_api_key else None
            )
    
    def check_main_index(self) -> bool:
        """检查主索引是否存在"""
        return self._client.indices.exists(index=self.main_index)
    
    def create_knowledge_base_alias(self, kb_id: str) -> bool:
        """
        为指定知识库创建ES别名和路由
        
        参数:
            kb_id: 知识库ID
        
        返回:
            操作是否成功
        """
        try:
            alias_name = f"kb_{kb_id}"
            
            # 创建别名，并设置路由和过滤器
            response = self._client.indices.put_alias(
                index=self.main_index,
                name=alias_name,
                body={
                    "routing": kb_id,
                    "filter": {
                        "term": {
                            "knowledge_base_id": kb_id
                        }
                    }
                }
            )
            
            logger.info(f"已为知识库 {kb_id} 创建别名和路由: {alias_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建知识库别名时出错: {str(e)}")
            return False
    
    def delete_knowledge_base_alias(self, kb_id: str) -> bool:
        """
        删除指定知识库的ES别名
        
        参数:
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            alias_name = f"kb_{kb_id}"
            
            # 先检查别名是否存在
            if not self._client.indices.exists_alias(name=alias_name):
                logger.warning(f"知识库别名不存在: {alias_name}")
                return True
                
            # 删除别名
            response = self._client.indices.delete_alias(
                index=self.main_index,
                name=alias_name
            )
            
            logger.info(f"已删除知识库别名: {alias_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除知识库别名时出错: {str(e)}")
            return False
    
    def get_all_kb_aliases(self) -> List[Dict[str, Any]]:
        """
        获取所有知识库别名
        
        返回:
            知识库别名列表
        """
        try:
            # 获取所有别名
            all_aliases = self._client.indices.get_alias(index=self.main_index)
            
            kb_aliases = []
            if self.main_index in all_aliases:
                for alias_name, alias_data in all_aliases[self.main_index]["aliases"].items():
                    if alias_name.startswith("kb_"):
                        kb_id = alias_name.replace("kb_", "")
                        kb_aliases.append({
                            "kb_id": kb_id,
                            "alias": alias_name,
                            "routing": alias_data.get("routing"),
                            "filter": alias_data.get("filter")
                        })
            
            return kb_aliases
            
        except Exception as e:
            logger.error(f"获取知识库别名时出错: {str(e)}")
            return []
    
    def index_document(self, doc_data: Dict[str, Any], kb_id: str) -> bool:
        """
        索引文档到Elasticsearch，使用知识库路由
        
        参数:
            doc_data: 文档数据
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            # 确保文档包含知识库ID
            if "knowledge_base_id" not in doc_data:
                doc_data["knowledge_base_id"] = kb_id
            
            # 使用路由参数索引文档
            response = self._client.index(
                index=self.main_index,
                id=doc_data.get("id"),
                body=doc_data,
                routing=kb_id
            )
            
            logger.debug(f"已索引文档: ID {doc_data.get('id')} 到知识库 {kb_id}")
            return True
            
        except Exception as e:
            logger.error(f"索引文档时出错: {str(e)}")
            return False
    
    def delete_kb_documents(self, kb_id: str) -> bool:
        """
        删除知识库中的所有文档
        
        参数:
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            # 使用delete_by_query删除匹配的文档
            response = self._client.delete_by_query(
                index=self.main_index,
                body={
                    "query": {
                        "term": {
                            "knowledge_base_id": kb_id
                        }
                    }
                },
                routing=kb_id  # 使用路由提高性能
            )
            
            logger.info(f"已删除知识库 {kb_id} 中的 {response.get('deleted', 0)} 个文档")
            return True
            
        except Exception as e:
            logger.error(f"删除知识库文档时出错: {str(e)}")
            return False
    
    def search_kb(
        self, 
        kb_id: str, 
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        在指定知识库中进行混合搜索
        
        参数:
            kb_id: 知识库ID
            query_text: 文本查询
            query_vector: 向量查询
            vector_weight: 向量搜索权重
            text_weight: 文本搜索权重
            top_k: 返回结果数量
            
        返回:
            搜索结果列表
        """
        try:
            # 构建搜索请求
            search_body = {}
            
            # 使用模板进行混合搜索
            if query_text and query_vector:
                # 混合搜索
                search_body = {
                    "id": "hybrid_search_template",
                    "params": {
                        "query_vector": query_vector,
                        "text_query": query_text,
                        "vector_boost": vector_weight,
                        "text_boost": text_weight,
                        "title_boost": 3.0,
                        "content_boost": 2.0,
                        "size": top_k,
                        "source_fields": ["id", "document_id", "title", "content", "metadata"]
                    }
                }
                
                # 执行搜索
                response = self._client.search_template(
                    index=f"kb_{kb_id}",  # 使用别名
                    body=search_body
                )
            elif query_vector:
                # 仅向量搜索
                search_body = {
                    "id": "vector_search_template",
                    "params": {
                        "query_vector": query_vector,
                        "size": top_k,
                        "source_fields": ["id", "document_id", "title", "content", "metadata"]
                    }
                }
                
                # 执行搜索
                response = self._client.search_template(
                    index=f"kb_{kb_id}",  # 使用别名
                    body=search_body
                )
            elif query_text:
                # 仅文本搜索
                search_body = {
                    "query": {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["title^3", "title.smartcn^2", "content^2", "content.smartcn"],
                            "operator": "OR",
                            "type": "best_fields"
                        }
                    },
                    "size": top_k,
                    "_source": ["id", "document_id", "title", "content", "metadata"],
                    "highlight": {
                        "fields": {
                            "title": {},
                            "content": {
                                "fragment_size": 150,
                                "number_of_fragments": 3
                            }
                        },
                        "pre_tags": ["<em>"],
                        "post_tags": ["</em>"]
                    }
                }
                
                # 执行搜索
                response = self._client.search(
                    index=f"kb_{kb_id}",  # 使用别名
                    body=search_body
                )
            else:
                logger.warning("文本查询和向量查询都为空")
                return []
            
            # 处理结果
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_source"]["id"],
                    "score": hit["_score"],
                    "content": hit["_source"].get("content", ""),
                    "title": hit["_source"].get("title", ""),
                    "metadata": hit["_source"].get("metadata", {}),
                    "document_id": hit["_source"].get("document_id", "")
                }
                
                # 添加高亮内容（如果有）
                if "highlight" in hit:
                    result["highlight"] = hit["highlight"]
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"知识库搜索时出错: {str(e)}")
            return []
    
    def search_multiple_kb(
        self,
        kb_ids: List[str],
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        在多个知识库中进行混合搜索
        
        参数:
            kb_ids: 知识库ID列表
            query_text: 文本查询
            query_vector: 向量查询
            vector_weight: 向量搜索权重
            text_weight: 文本搜索权重
            top_k: 返回结果数量
            
        返回:
            搜索结果列表
        """
        try:
            if not kb_ids:
                logger.warning("未提供知识库ID")
                return []
            
            # 构建别名列表
            kb_aliases = [f"kb_{kb_id}" for kb_id in kb_ids]
            
            # 构建搜索请求
            search_body = {}
            
            # 使用模板进行混合搜索
            if query_text and query_vector:
                # 混合搜索
                search_body = {
                    "id": "hybrid_search_template",
                    "params": {
                        "query_vector": query_vector,
                        "text_query": query_text,
                        "vector_boost": vector_weight,
                        "text_boost": text_weight,
                        "title_boost": 3.0,
                        "content_boost": 2.0,
                        "size": top_k,
                        "source_fields": ["id", "document_id", "title", "content", "metadata", "knowledge_base_id"]
                    }
                }
                
                # 执行搜索
                response = self._client.search_template(
                    index=",".join(kb_aliases),  # 使用多个别名
                    body=search_body
                )
            elif query_vector:
                # 仅向量搜索
                search_body = {
                    "id": "vector_search_template",
                    "params": {
                        "query_vector": query_vector,
                        "size": top_k,
                        "source_fields": ["id", "document_id", "title", "content", "metadata", "knowledge_base_id"]
                    }
                }
                
                # 执行搜索
                response = self._client.search_template(
                    index=",".join(kb_aliases),  # 使用多个别名
                    body=search_body
                )
            elif query_text:
                # 仅文本搜索
                search_body = {
                    "query": {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["title^3", "title.smartcn^2", "content^2", "content.smartcn"],
                            "operator": "OR",
                            "type": "best_fields"
                        }
                    },
                    "size": top_k,
                    "_source": ["id", "document_id", "title", "content", "metadata", "knowledge_base_id"],
                    "highlight": {
                        "fields": {
                            "title": {},
                            "content": {
                                "fragment_size": 150,
                                "number_of_fragments": 3
                            }
                        },
                        "pre_tags": ["<em>"],
                        "post_tags": ["</em>"]
                    }
                }
                
                # 执行搜索
                response = self._client.search(
                    index=",".join(kb_aliases),  # 使用多个别名
                    body=search_body
                )
            else:
                logger.warning("文本查询和向量查询都为空")
                return []
            
            # 处理结果
            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_source"]["id"],
                    "score": hit["_score"],
                    "content": hit["_source"].get("content", ""),
                    "title": hit["_source"].get("title", ""),
                    "metadata": hit["_source"].get("metadata", {}),
                    "document_id": hit["_source"].get("document_id", ""),
                    "knowledge_base_id": hit["_source"].get("knowledge_base_id", "")
                }
                
                # 添加高亮内容（如果有）
                if "highlight" in hit:
                    result["highlight"] = hit["highlight"]
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"多知识库搜索时出错: {str(e)}")
            return []

# 全局单例实例
_es_manager = None

def get_elasticsearch_manager() -> ElasticsearchManager:
    """获取ElasticsearchManager的单例实例"""
    global _es_manager
    if _es_manager is None:
        _es_manager = ElasticsearchManager()
    return _es_manager
