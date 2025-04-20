"""
LlamaIndex Indexing Module: Handles document indexing and structured data retrieval
Leverages LlamaIndex's strengths in hierarchical indexing and context-aware retrieval
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import os

from llama_index.core import (
    Document, 
    VectorStoreIndex, 
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage
)
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.vector_stores.milvus import MilvusVectorStore
from app.config import settings

def get_node_parser():
    """Get a LlamaIndex node parser with configured chunk size"""
    chunk_size = settings.LLAMAINDEX_CHUNK_SIZE
    chunk_overlap = settings.LLAMAINDEX_CHUNK_OVERLAP
    
    return SimpleNodeParser.from_defaults(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

def get_milvus_vector_store(collection_name: Optional[str] = None):
    """Get a Milvus vector store for LlamaIndex"""
    collection = collection_name or settings.MILVUS_COLLECTION
    
    # Connect to Milvus
    return MilvusVectorStore(
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
        collection_name=collection,
        dim=1536  # Dimension for OpenAI embeddings
    )

def create_document_index(
    documents: List[Dict[str, Any]],
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None
) -> VectorStoreIndex:
    """
    Create a LlamaIndex from documents
    
    Args:
        documents: List of document dictionaries with 'content' and 'metadata' keys
        collection_name: Optional Milvus collection name
        persist_dir: Optional directory to persist the index
        
    Returns:
        LlamaIndex VectorStoreIndex
    """
    # Convert to LlamaIndex document objects
    llamaindex_docs = []
    for doc in documents:
        llamaindex_docs.append(
            Document(
                text=doc.get("content", ""),
                metadata=doc.get("metadata", {})
            )
        )
    
    # Create parser
    parser = get_node_parser()
    nodes = parser.get_nodes_from_documents(llamaindex_docs)
    
    # Create vector store
    vector_store = get_milvus_vector_store(collection_name)
    
    # Create index
    index = VectorStoreIndex(
        nodes=nodes,
        vector_store=vector_store
    )
    
    # Persist index if directory is provided
    if persist_dir:
        os.makedirs(persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=persist_dir)
    
    return index

def load_or_create_index(
    documents: Optional[List[Dict[str, Any]]] = None,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None
) -> VectorStoreIndex:
    """
    Load an existing index or create a new one
    
    Args:
        documents: Optional documents to index if creating new index
        collection_name: Optional Milvus collection name
        persist_dir: Optional directory where the index is persisted
        
    Returns:
        LlamaIndex VectorStoreIndex
    """
    # Try to load existing index
    if persist_dir and os.path.exists(persist_dir):
        try:
            # Create vector store
            vector_store = get_milvus_vector_store(collection_name)
            
            # Create storage context
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=persist_dir
            )
            
            # Load index
            return load_index_from_storage(storage_context)
        
        except Exception as e:
            print(f"Error loading index: {e}")
            # Fall back to creating new index
    
    # Create new index
    if documents:
        return create_document_index(documents, collection_name, persist_dir)
    else:
        raise ValueError("Documents must be provided if no existing index is found")

def index_document(
    document: Dict[str, Any],
    index: Optional[VectorStoreIndex] = None,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None
) -> VectorStoreIndex:
    """
    Index a single document, either updating an existing index or creating a new one
    
    Args:
        document: Document dictionary with 'content' and 'metadata' keys
        index: Optional existing index to update
        collection_name: Optional Milvus collection name
        persist_dir: Optional directory to persist the index
        
    Returns:
        Updated LlamaIndex VectorStoreIndex
    """
    # Create LlamaIndex document
    llamaindex_doc = Document(
        text=document.get("content", ""),
        metadata=document.get("metadata", {})
    )
    
    # Create parser and extract nodes
    parser = get_node_parser()
    nodes = parser.get_nodes_from_documents([llamaindex_doc])
    
    # If index exists, insert nodes
    if index:
        for node in nodes:
            index.insert(node)
        
        # Persist if directory is provided
        if persist_dir:
            index.storage_context.persist(persist_dir=persist_dir)
        
        return index
    
    # Otherwise create new index
    return create_document_index([document], collection_name, persist_dir)

def index_directory(
    directory_path: str,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    file_extns: Optional[List[str]] = None
) -> VectorStoreIndex:
    """
    Index all documents in a directory
    
    Args:
        directory_path: Path to directory containing documents
        collection_name: Optional Milvus collection name
        persist_dir: Optional directory to persist the index
        file_extns: Optional list of file extensions to include
        
    Returns:
        LlamaIndex VectorStoreIndex
    """
    # Default file extensions if not provided
    if file_extns is None:
        file_extns = [".txt", ".pdf", ".md", ".docx", ".csv", ".html"]
    
    # Load documents from directory
    reader = SimpleDirectoryReader(
        input_dir=directory_path,
        required_exts=file_extns
    )
    documents = reader.load_data()
    
    # Create parser
    parser = get_node_parser()
    nodes = parser.get_nodes_from_documents(documents)
    
    # Create vector store
    vector_store = get_milvus_vector_store(collection_name)
    
    # Create index
    index = VectorStoreIndex(
        nodes=nodes,
        vector_store=vector_store
    )
    
    # Persist index if directory is provided
    if persist_dir:
        os.makedirs(persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=persist_dir)
    
    return index
