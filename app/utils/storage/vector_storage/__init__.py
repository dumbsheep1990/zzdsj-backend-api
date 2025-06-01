"""
向量存储模块
提供向量存储和搜索功能
"""

from .store import VectorStore, get_vector_store, create_vector_store
from .milvus_adapter import MilvusVectorStore
from .legacy_support import init_milvus, get_collection, add_vectors, search_similar_vectors

__all__ = [
    # 新接口
    "VectorStore",
    "get_vector_store", 
    "create_vector_store",
    "MilvusVectorStore",
    
    # 向后兼容接口
    "init_milvus",
    "get_collection",
    "add_vectors", 
    "search_similar_vectors"
] 