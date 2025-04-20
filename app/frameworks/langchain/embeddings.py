from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from app.config import settings

def get_embedding_model():
    """
    获取LangChain的嵌入模型。
    """
    # 使用API密钥初始化OpenAI嵌入
    return OpenAIEmbeddings(
        openai_api_key=settings.OPENAI_API_KEY,
        model="text-embedding-ada-002"  # 您可以更改为其他嵌入模型
    )

def create_embedding(text: str) -> List[float]:
    """
    为单个文本创建嵌入。
    """
    embeddings = get_embedding_model()
    return embeddings.embed_query(text)

def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    为多个文本创建嵌入。
    """
    embeddings = get_embedding_model()
    return embeddings.embed_documents(texts)

def similarity_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    使用嵌入搜索相似文档。
    """
    import os
    import faiss
    import numpy as np
    import pickle
    
    # 向量存储路径
    index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss_index.idx")
    metadata_path = os.path.join(settings.VECTOR_STORE_PATH, "metadata.pkl")
    
    # 检查索引是否存在
    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        return []
    
    # 创建查询嵌入
    query_embedding = create_embedding(query)
    query_embedding_np = np.array([query_embedding], dtype=np.float32)
    
    # 加载索引
    index = faiss.read_index(index_path)
    
    # 加载元数据
    with open(metadata_path, 'rb') as f:
        stored_metadata = pickle.load(f)
        stored_texts = pickle.load(f)
    
    # 搜索索引
    D, I = index.search(query_embedding_np, top_k)
    
    # 编译结果
    results = []
    for i, idx in enumerate(I[0]):
        if idx < len(stored_texts) and idx >= 0:
            results.append({
                "content": stored_texts[idx],
                "metadata": stored_metadata[idx],
                "score": float(D[0][i])
            })
    
    return results
