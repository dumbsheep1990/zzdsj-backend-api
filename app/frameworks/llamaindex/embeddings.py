"""
LlamaIndex嵌入模块: 提供文本嵌入和相似度搜索功能
替代LangChain的嵌入功能
"""

from typing import List, Dict, Any, Optional
from llama_index.embeddings.openai import OpenAIEmbedding
from app.config import settings
import os
import logging

logger = logging.getLogger(__name__)

def get_embedding_model():
    """
    获取LlamaIndex的嵌入模型，替代LangChain的OpenAIEmbeddings
    """
    return OpenAIEmbedding(
        api_key=settings.OPENAI_API_KEY,
        model_name="text-embedding-ada-002"
    )

def create_embedding(text: str) -> List[float]:
    """
    为单个文本创建嵌入，替代LangChain功能
    """
    embeddings = get_embedding_model()
    return embeddings.get_text_embedding(text)

def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    为多个文本创建嵌入，替代LangChain功能
    """
    embeddings = get_embedding_model()
    return [embeddings.get_text_embedding(text) for text in texts]

def similarity_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    使用嵌入搜索相似文档，替代LangChain功能
    """
    try:
        from app.frameworks.llamaindex.retrieval import get_query_engine
        from app.frameworks.llamaindex.indexing import load_or_create_index
        
        # 加载索引 
        index = load_or_create_index(collection_name="default")
        
        # 创建查询引擎
        engine = get_query_engine(
            index,
            similarity_top_k=top_k,
            similarity_cutoff=0.7
        )
        
        # 查询
        response = engine.query(query)
        
        # 格式化结果
        results = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                results.append({
                    "content": node.text,
                    "metadata": node.metadata,
                    "score": node.score if node.score is not None else 1.0
                })
                
        return results
    
    except Exception as e:
        logger.error(f"相似度搜索时出错: {str(e)}")
        return []
