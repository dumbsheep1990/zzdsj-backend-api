"""
向量存储向后兼容支持
提供旧版本接口的兼容性实现，将调用重定向到新的标准化组件
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

# 导入新的标准化组件
from .standard_initializer import (
    init_standard_document_collection,
    VectorStoreFactory
)
from .store import get_vector_store

logger = logging.getLogger(__name__)

def _get_settings():
    """懒加载settings，避免循环导入"""
    try:
        from app.config import settings
        return settings
    except ImportError:
        # 如果导入失败，创建默认配置
        class DefaultSettings:
            MILVUS_HOST = "localhost"
            MILVUS_PORT = 19530
            MILVUS_COLLECTION = "document_vectors"
        
        return DefaultSettings()

def init_milvus():
    """
    向后兼容的Milvus初始化函数
    优先使用新的标准化方法，失败时使用原始方法
    """
    logger.info("开始初始化Milvus（向后兼容模式）...")
    
    settings = _get_settings()
    
    try:
        # 使用新的标准化初始化
        success = init_standard_document_collection(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            collection_name=settings.MILVUS_COLLECTION,
            dimension=1536
        )
        
        if success:
            logger.info("✅ 使用标准化方法初始化Milvus成功")
            return
        else:
            logger.warning("标准化初始化失败，回退到原始方法")
            
    except Exception as e:
        logger.warning(f"标准化初始化异常: {str(e)}，回退到原始方法")
    
    # 回退到原始方法
    try:
        from pymilvus import connections, utility
        from .milvus_adapter import MilvusVectorStore
        
        connections.connect(
            alias="default", 
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        
        # 检查集合是否存在，如果不存在则创建
        if not utility.has_collection(settings.MILVUS_COLLECTION):
            _create_legacy_collection()
            
        logger.info("✅ 使用原始方法初始化Milvus成功")
        
    except Exception as e:
        logger.error(f"所有初始化方法都失败: {str(e)}")
        raise

def _create_legacy_collection(dim=1536):
    """创建向后兼容的集合"""
    from pymilvus import FieldSchema, CollectionSchema, DataType, Collection
    
    settings = _get_settings()
    
    logger.info(f"创建向后兼容的Milvus集合: {settings.MILVUS_COLLECTION}, 维度: {dim}")
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="chunk_id", dtype=DataType.INT64),
        FieldSchema(name="document_id", dtype=DataType.INT64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
    ]
    
    schema = CollectionSchema(fields=fields, description="文档嵌入集合")
    collection = Collection(name=settings.MILVUS_COLLECTION, schema=schema)
    
    # 为向量字段创建索引
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    
    return collection

def get_collection():
    """
    向后兼容的获取集合函数
    """
    try:
        # 优先使用新的向量存储接口
        vector_store = get_vector_store()
        if hasattr(vector_store, 'get_collection'):
            return vector_store.get_collection()
    except Exception as e:
        logger.warning(f"新接口获取集合失败: {str(e)}，使用原始方法")
    
    # 回退到原始方法
    from pymilvus import Collection, utility
    
    settings = _get_settings()
    
    if not utility.has_collection(settings.MILVUS_COLLECTION):
        return _create_legacy_collection()
    
    return Collection(name=settings.MILVUS_COLLECTION)

def add_vectors(chunk_ids: List[int], document_ids: List[int], vectors: List[List[float]]):
    """
    向后兼容的添加向量函数
    """
    try:
        # 优先使用新的向量存储接口
        vector_store = get_vector_store()
        
        # 将数据转换为新接口格式
        documents = []
        for i, (chunk_id, doc_id, vector) in enumerate(zip(chunk_ids, document_ids, vectors)):
            documents.append({
                "id": f"{doc_id}_{chunk_id}",
                "text": f"document_{doc_id}_chunk_{chunk_id}",  # 占位文本
                "vector": vector,
                "metadata": {
                    "chunk_id": chunk_id,
                    "document_id": doc_id
                }
            })
        
        vector_store.add_documents(documents)
        logger.debug("使用新接口添加向量成功")
        
    except Exception as e:
        logger.warning(f"新接口添加向量失败: {str(e)}，使用原始方法")
        
        # 回退到原始方法
        collection = get_collection()
        
        # 准备插入数据
        data = [
            chunk_ids,      # chunk_id字段
            document_ids,   # document_id字段
            vectors         # embedding字段
        ]
        
        # 插入数据
        collection.insert(data)
        collection.flush()
        logger.debug("使用原始方法添加向量成功")

def search_similar_vectors(query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    向后兼容的搜索相似向量函数
    """
    try:
        # 优先使用新的向量存储接口
        vector_store = get_vector_store()
        
        results = vector_store.search(
            query_vector=query_vector,
            top_k=top_k
        )
        
        # 转换为旧接口格式
        formatted_results = []
        for result in results:
            metadata = result.get("metadata", {})
            formatted_results.append({
                "chunk_id": metadata.get("chunk_id"),
                "document_id": metadata.get("document_id"),
                "score": result.get("score", 0.0)
            })
        
        return formatted_results
        
    except Exception as e:
        logger.warning(f"新接口搜索失败: {str(e)}，使用原始方法")
        
        # 回退到原始方法
        collection = get_collection()
        collection.load()
        
        # 如需要转换为numpy数组
        if not isinstance(query_vector, np.ndarray):
            query_vector = np.array([query_vector])
        
        # 执行搜索
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=query_vector, 
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["chunk_id", "document_id"]
        )
        
        # 格式化结果
        formatted_results = []
        for hits in results:
            for hit in hits:
                formatted_results.append({
                    "chunk_id": hit.entity.get("chunk_id"),
                    "document_id": hit.entity.get("document_id"),
                    "score": hit.distance
                })
        
        return formatted_results

# 向后兼容的类和函数导出
__all__ = [
    "init_milvus",
    "get_collection",
    "add_vectors",
    "search_similar_vectors"
] 