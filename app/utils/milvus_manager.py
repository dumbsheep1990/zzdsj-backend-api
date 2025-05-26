"""
Milvus向量数据库管理模块: 实现基于知识库的分区管理
支持高效的知识库隔离与向量检索
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import numpy as np
import json
from datetime import datetime

from pymilvus import (
    connections, 
    utility,
    FieldSchema, 
    CollectionSchema, 
    DataType,
    Collection
)
from app.config import settings

logger = logging.getLogger(__name__)

class MilvusManager:
    """Milvus向量数据库管理类，提供分区支持"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
        dimension: int = 1536  # 默认OpenAI向量维度
    ):
        """
        初始化Milvus管理器
        
        参数:
            host: Milvus服务器地址
            port: Milvus服务器端口
            collection_name: 集合名称
            dimension: 向量维度
        """
        self.host = host or settings.MILVUS_HOST
        self.port = port or settings.MILVUS_PORT
        self.collection_name = collection_name or settings.MILVUS_COLLECTION
        self.dimension = dimension
        
        # 连接Milvus
        self._connect()
        
        # 获取或创建集合
        self.collection = self._get_or_create_collection()
    
    def _connect(self) -> None:
        """连接到Milvus服务器"""
        try:
            connections.connect(
                alias="default", 
                host=self.host,
                port=self.port
            )
            logger.info(f"已连接到Milvus服务器: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"连接Milvus服务器失败: {str(e)}")
            raise
    
    def _get_or_create_collection(self) -> Collection:
        """获取或创建Milvus集合"""
        try:
            # 检查集合是否存在
            if utility.has_collection(self.collection_name):
                logger.info(f"已加载现有集合: {self.collection_name}")
                collection = Collection(name=self.collection_name)
                
                # 检查集合是否已加载
                if not collection.is_loaded:
                    collection.load()
                
                return collection
            
            # 创建新集合
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="knowledge_base_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            
            schema = CollectionSchema(fields=fields, description="文档向量集合")
            collection = Collection(name=self.collection_name, schema=schema)
            
            # 创建索引
            index_params = {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {
                    "M": 16,
                    "efConstruction": 200
                }
            }
            collection.create_index(field_name="vector", index_params=index_params)
            
            # 加载集合
            collection.load()
            
            logger.info(f"成功创建集合: {self.collection_name}")
            return collection
            
        except Exception as e:
            logger.error(f"获取或创建Milvus集合失败: {str(e)}")
            raise
    
    def create_kb_partition(self, kb_id: str) -> bool:
        """
        为知识库创建Milvus分区
        
        参数:
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            partition_name = f"kb_{kb_id}"
            
            # 检查分区是否已存在
            if self.collection.has_partition(partition_name):
                logger.info(f"分区已存在: {partition_name}")
                return True
            
            # 创建新分区
            self.collection.create_partition(partition_name=partition_name)
            logger.info(f"成功创建分区: {partition_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建知识库分区失败: {str(e)}")
            return False
    
    def delete_kb_partition(self, kb_id: str) -> bool:
        """
        删除知识库分区
        
        参数:
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            partition_name = f"kb_{kb_id}"
            
            # 检查分区是否存在
            if not self.collection.has_partition(partition_name):
                logger.info(f"分区不存在: {partition_name}")
                return True
            
            # 删除分区
            self.collection.drop_partition(partition_name=partition_name)
            logger.info(f"成功删除分区: {partition_name}")
            return True
            
        except Exception as e:
            logger.error(f"删除知识库分区失败: {str(e)}")
            return False
    
    def get_kb_partitions(self) -> List[str]:
        """
        获取所有知识库分区
        
        返回:
            分区名称列表
        """
        try:
            partitions = self.collection.partitions
            kb_partitions = []
            
            for partition in partitions:
                if partition.name.startswith("kb_"):
                    kb_partitions.append(partition.name)
            
            return kb_partitions
            
        except Exception as e:
            logger.error(f"获取知识库分区失败: {str(e)}")
            return []
    
    def insert_vector(
        self, 
        id: str,
        document_id: str,
        knowledge_base_id: str,
        chunk_id: str,
        vector: List[float],
        text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        向知识库分区插入向量
        
        参数:
            id: 唯一ID
            document_id: 文档ID
            knowledge_base_id: 知识库ID
            chunk_id: 分块ID
            vector: 向量数据
            text: 文本内容
            metadata: 元数据
            
        返回:
            操作是否成功
        """
        try:
            partition_name = f"kb_{knowledge_base_id}"
            
            # 确保分区存在
            if not self.collection.has_partition(partition_name):
                self.create_kb_partition(knowledge_base_id)
            
            # 准备插入数据
            entities = [
                [id],                      # id
                [document_id],             # document_id
                [knowledge_base_id],       # knowledge_base_id
                [chunk_id],                # chunk_id
                [vector],                  # vector
                [text],                    # text
                [json.dumps(metadata)]     # metadata
            ]
            
            # 插入到特定分区
            self.collection.insert(entities, partition_name=partition_name)
            return True
            
        except Exception as e:
            logger.error(f"插入向量失败: {str(e)}")
            return False
    
    def batch_insert_vectors(
        self,
        data: List[Dict[str, Any]],
        knowledge_base_id: str
    ) -> bool:
        """
        批量向知识库分区插入向量
        
        参数:
            data: 向量数据列表
            knowledge_base_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            if not data:
                return True
                
            partition_name = f"kb_{knowledge_base_id}"
            
            # 确保分区存在
            if not self.collection.has_partition(partition_name):
                self.create_kb_partition(knowledge_base_id)
            
            # 准备批量插入数据
            ids = []
            document_ids = []
            kb_ids = []
            chunk_ids = []
            vectors = []
            texts = []
            metadatas = []
            
            for item in data:
                ids.append(item["id"])
                document_ids.append(item["document_id"])
                kb_ids.append(knowledge_base_id)
                chunk_ids.append(item["chunk_id"])
                vectors.append(item["vector"])
                texts.append(item["text"])
                metadatas.append(json.dumps(item.get("metadata", {})))
            
            # 封装为实体列表
            entities = [
                ids,         # id
                document_ids, # document_id
                kb_ids,      # knowledge_base_id
                chunk_ids,   # chunk_id
                vectors,     # vector
                texts,       # text
                metadatas    # metadata
            ]
            
            # 批量插入到特定分区
            self.collection.insert(entities, partition_name=partition_name)
            return True
            
        except Exception as e:
            logger.error(f"批量插入向量失败: {str(e)}")
            return False
    
    def delete_kb_vectors(self, kb_id: str) -> bool:
        """
        删除知识库中的所有向量
        
        参数:
            kb_id: 知识库ID
            
        返回:
            操作是否成功
        """
        try:
            partition_name = f"kb_{kb_id}"
            
            # 检查分区是否存在
            if not self.collection.has_partition(partition_name):
                logger.info(f"分区不存在: {partition_name}")
                return True
            
            # 执行删除
            expr = f'knowledge_base_id == "{kb_id}"'
            self.collection.delete(expr, partition_name=partition_name)
            logger.info(f"成功删除知识库 {kb_id} 中的向量")
            return True
            
        except Exception as e:
            logger.error(f"删除知识库向量失败: {str(e)}")
            return False
    
    def search_vectors(
        self,
        kb_id: str,
        query_vector: List[float],
        top_k: int = 10,
        expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        在知识库中搜索向量
        
        参数:
            kb_id: 知识库ID
            query_vector: 查询向量
            top_k: 返回结果数量
            expr: 可选的过滤表达式
            
        返回:
            搜索结果列表
        """
        try:
            partition_name = f"kb_{kb_id}"
            
            # 检查分区是否存在
            if not self.collection.has_partition(partition_name):
                logger.warning(f"分区不存在: {partition_name}")
                return []
            
            # 确保分区已加载
            if not self.collection.is_loaded:
                self.collection.load()
            
            # 搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 100}
            }
            
            # 执行搜索
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                partition_names=[partition_name],
                output_fields=["document_id", "chunk_id", "text", "metadata"]
            )
            
            # 处理结果
            formatted_results = []
            for hits in results:
                for i, hit in enumerate(hits):
                    # 尝试解析JSON元数据
                    try:
                        metadata = json.loads(hit.entity.get("metadata", "{}"))
                    except:
                        metadata = {}
                    
                    result = {
                        "id": hit.id,
                        "score": hit.score,
                        "document_id": hit.entity.get("document_id", ""),
                        "chunk_id": hit.entity.get("chunk_id", ""),
                        "text": hit.entity.get("text", ""),
                        "metadata": metadata,
                        "knowledge_base_id": kb_id
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索向量失败: {str(e)}")
            return []
    
    def search_multiple_kb(
        self,
        kb_ids: List[str],
        query_vector: List[float],
        top_k: int = 10,
        expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        在多个知识库中搜索向量
        
        参数:
            kb_ids: 知识库ID列表
            query_vector: 查询向量
            top_k: 返回结果数量
            expr: 可选的过滤表达式
            
        返回:
            搜索结果列表
        """
        try:
            if not kb_ids:
                logger.warning("未提供知识库ID")
                return []
            
            # 构建分区列表
            partition_names = [f"kb_{kb_id}" for kb_id in kb_ids]
            valid_partitions = []
            
            # 验证分区是否存在
            for partition in partition_names:
                if self.collection.has_partition(partition):
                    valid_partitions.append(partition)
            
            if not valid_partitions:
                logger.warning("没有有效的知识库分区")
                return []
            
            # 确保分区已加载
            if not self.collection.is_loaded:
                self.collection.load()
            
            # 搜索参数
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 100}
            }
            
            # 执行搜索
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=expr,
                partition_names=valid_partitions,
                output_fields=["document_id", "chunk_id", "text", "metadata", "knowledge_base_id"]
            )
            
            # 处理结果
            formatted_results = []
            for hits in results:
                for i, hit in enumerate(hits):
                    # 尝试解析JSON元数据
                    try:
                        metadata = json.loads(hit.entity.get("metadata", "{}"))
                    except:
                        metadata = {}
                    
                    result = {
                        "id": hit.id,
                        "score": hit.score,
                        "document_id": hit.entity.get("document_id", ""),
                        "chunk_id": hit.entity.get("chunk_id", ""),
                        "text": hit.entity.get("text", ""),
                        "metadata": metadata,
                        "knowledge_base_id": hit.entity.get("knowledge_base_id", "")
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"多知识库搜索向量失败: {str(e)}")
            return []

# 全局单例实例
_milvus_manager = None

def get_milvus_manager() -> MilvusManager:
    """获取MilvusManager的单例实例"""
    global _milvus_manager
    if _milvus_manager is None:
        _milvus_manager = MilvusManager()
    return _milvus_manager
