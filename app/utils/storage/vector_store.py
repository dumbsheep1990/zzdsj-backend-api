from typing import List, Dict, Any, Optional
import numpy as np
from pymilvus import (
    connections, 
    utility,
    FieldSchema, 
    CollectionSchema, 
    DataType,
    Collection
)
from app.config import settings

def init_milvus():
    """初始化Milvus向量数据库连接"""
    connections.connect(
        alias="default", 
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT
    )
    
    # 检查集合是否存在，如果不存在则创建
    if not utility.has_collection(settings.MILVUS_COLLECTION):
        create_collection()

def create_collection(dim=1536):  # OpenAI嵌入的默认维度
    """创建用于文档嵌入的Milvus集合"""
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
    """获取Milvus集合，如有必要则创建"""
    if not utility.has_collection(settings.MILVUS_COLLECTION):
        return create_collection()
    
    return Collection(name=settings.MILVUS_COLLECTION)

def add_vectors(chunk_ids: List[int], document_ids: List[int], vectors: List[List[float]]):
    """向Milvus集合添加向量"""
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

def search_similar_vectors(query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """在Milvus中搜索相似向量"""
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
