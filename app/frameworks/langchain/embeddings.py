from typing import List, Dict, Any, Optional
from langchain_openai import OpenAIEmbeddings
from app.config import settings

def get_embedding_model():
    """
    Get the embedding model from LangChain.
    """
    # Initialize OpenAI embeddings with API key
    return OpenAIEmbeddings(
        openai_api_key=settings.OPENAI_API_KEY,
        model="text-embedding-ada-002"  # You can change this to a different embedding model
    )

def create_embedding(text: str) -> List[float]:
    """
    Create an embedding for a single text.
    """
    embeddings = get_embedding_model()
    return embeddings.embed_query(text)

def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for multiple texts.
    """
    embeddings = get_embedding_model()
    return embeddings.embed_documents(texts)

def similarity_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search for similar documents using embeddings.
    """
    import os
    import faiss
    import numpy as np
    import pickle
    
    # Path for vector store
    index_path = os.path.join(settings.VECTOR_STORE_PATH, "faiss_index.idx")
    metadata_path = os.path.join(settings.VECTOR_STORE_PATH, "metadata.pkl")
    
    # Check if index exists
    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        return []
    
    # Create query embedding
    query_embedding = create_embedding(query)
    query_embedding_np = np.array([query_embedding], dtype=np.float32)
    
    # Load index
    index = faiss.read_index(index_path)
    
    # Load metadata
    with open(metadata_path, 'rb') as f:
        stored_metadata = pickle.load(f)
        stored_texts = pickle.load(f)
    
    # Search index
    D, I = index.search(query_embedding_np, top_k)
    
    # Compile results
    results = []
    for i, idx in enumerate(I[0]):
        if idx < len(stored_texts) and idx >= 0:
            results.append({
                "content": stored_texts[idx],
                "metadata": stored_metadata[idx],
                "score": float(D[0][i])
            })
    
    return results
