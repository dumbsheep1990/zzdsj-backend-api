"""
向量存储模块 - 向后兼容桥接
此文件提供向后兼容的接口，将旧的调用重定向到新的标准化组件
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

# 导入新的标准化组件
from app.utils.storage.vector_storage import (
    init_milvus as new_init_milvus,
    get_collection as new_get_collection,
    add_vectors as new_add_vectors,
    search_similar_vectors as new_search_similar_vectors,
    init_standard_document_collection,
    VectorStoreFactory
)

# 导入原始的pymilvus组件用于兼容性
from pymilvus import (
    connections, 
    utility,
    FieldSchema, 
    CollectionSchema, 
    DataType,
    Collection
)

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
    初始化Milvus向量数据库连接
    优先使用新的标准化方法，失败时回退到原始方法
    """
    logger.info("开始初始化Milvus（兼容模式）...")
    
    settings = _get_settings()
    
    try:
        # 优先尝试使用新的标准化初始化
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
        connections.connect(
            alias="default", 
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        
        # 检查集合是否存在，如果不存在则创建
        if not utility.has_collection(settings.MILVUS_COLLECTION):
            create_collection()
            
        logger.info("✅ 使用原始方法初始化Milvus成功")
        
    except Exception as e:
        logger.error(f"原始方法初始化也失败: {str(e)}")
        raise

def create_collection(dim=1536):  
    """
    创建用于文档嵌入的Milvus集合
    保持原有接口兼容性
    """
    settings = _get_settings()
    
    logger.info(f"创建Milvus集合: {settings.MILVUS_COLLECTION}, 维度: {dim}")
    
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
    获取Milvus集合，如有必要则创建
    保持原有接口兼容性
    """
    try:
        # 优先尝试使用新的接口
        return new_get_collection()
    except Exception as e:
        logger.warning(f"新接口获取集合失败: {str(e)}，使用原始方法")
        
        # 回退到原始方法
        settings = _get_settings()
        
        if not utility.has_collection(settings.MILVUS_COLLECTION):
            return create_collection()
        
        return Collection(name=settings.MILVUS_COLLECTION)

def add_vectors(chunk_ids: List[int], document_ids: List[int], vectors: List[List[float]]):
    """
    向Milvus集合添加向量
    保持原有接口兼容性
    """
    try:
        # 优先尝试使用新的接口
        new_add_vectors(chunk_ids, document_ids, vectors)
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
    在Milvus中搜索相似向量
    保持原有接口兼容性
    """
    try:
        # 优先尝试使用新的接口
        return new_search_similar_vectors(query_vector, top_k)
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

# 为了完全向后兼容，导出新的标准化方法供高级用户使用
__all__ = [
    "init_milvus",
    "create_collection", 
    "get_collection",
    "add_vectors",
    "search_similar_vectors",
    # 新的标准化方法
    "init_standard_document_collection",
    "VectorStoreFactory"
]
