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
    """Initialize connection to Milvus vector database"""
    connections.connect(
        alias="default", 
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT
    )
    
    # Check if collection exists, create if it doesn't
    if not utility.has_collection(settings.MILVUS_COLLECTION):
        create_collection()

def create_collection(dim=1536):  # Default dimension for OpenAI embeddings
    """Create the Milvus collection for document embeddings"""
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="chunk_id", dtype=DataType.INT64),
        FieldSchema(name="document_id", dtype=DataType.INT64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim)
    ]
    
    schema = CollectionSchema(fields=fields, description="Document embeddings collection")
    collection = Collection(name=settings.MILVUS_COLLECTION, schema=schema)
    
    # Create index for vector field
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    
    return collection

def get_collection():
    """Get the Milvus collection, creating it if necessary"""
    if not utility.has_collection(settings.MILVUS_COLLECTION):
        return create_collection()
    
    return Collection(name=settings.MILVUS_COLLECTION)

def add_vectors(chunk_ids: List[int], document_ids: List[int], vectors: List[List[float]]):
    """Add vectors to Milvus collection"""
    collection = get_collection()
    
    # Prepare data for insertion
    data = [
        chunk_ids,      # chunk_id field
        document_ids,   # document_id field
        vectors         # embedding field
    ]
    
    # Insert data
    collection.insert(data)
    collection.flush()

def search_similar_vectors(query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """Search for similar vectors in Milvus"""
    collection = get_collection()
    collection.load()
    
    # Convert to numpy array if needed
    if not isinstance(query_vector, np.ndarray):
        query_vector = np.array([query_vector])
    
    # Perform search
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
    results = collection.search(
        data=query_vector, 
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["chunk_id", "document_id"]
    )
    
    # Format results
    formatted_results = []
    for hits in results:
        for hit in hits:
            formatted_results.append({
                "chunk_id": hit.entity.get("chunk_id"),
                "document_id": hit.entity.get("document_id"),
                "score": hit.distance
            })
    
    return formatted_results
