"""
LlamaIndex嵌入模块: 提供嵌入生成和相似度搜索功能
替代LangChain的嵌入功能
"""

from typing import List, Dict, Any, Optional
import os
import numpy as np
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import VectorStoreIndex, Document
from llama_index.vector_stores.faiss import FaissVectorStore
from app.config import settings

def get_embedding_model():
    """获取LlamaIndex嵌入模型，替代LangChain的OpenAIEmbeddings"""
    return OpenAIEmbedding(
        api_key=settings.OPENAI_API_KEY,
        model_name="text-embedding-ada-002"
    )

def create_embedding(text: str) -> List[float]:
    """为单个文本创建嵌入"""
    embed_model = get_embedding_model()
    return embed_model.get_text_embedding(text)

def create_embeddings(texts: List[str]) -> List[List[float]]:
    """为多个文本创建嵌入"""
    embed_model = get_embedding_model()
    return embed_model.get_text_embedding_batch(texts)

def similarity_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    使用嵌入搜索相似文档，替代LangChain的相似度搜索
    """
    # 向量存储路径
    index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss_index")
    metadata_path = os.path.join(settings.VECTOR_STORE_PATH, "metadata.json")
    
    # 检查索引是否存在
    if not os.path.exists(index_path):
        return []
    
    # 创建嵌入模型
    embed_model = get_embedding_model()
    
    # 加载向量存储
    vector_store = FaissVectorStore.from_persist_dir(index_path)
    
    # 创建索引
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed_model
    )
    
    # 创建检索器
    retriever = index.as_retriever(similarity_top_k=top_k)
    
    # 执行查询
    query_results = retriever.retrieve(query)
    
    # 转换结果
    results = []
    for node in query_results:
        results.append({
            "content": node.text,
            "metadata": node.metadata,
            "score": node.score if node.score is not None else 1.0,
        })
    
    return results
