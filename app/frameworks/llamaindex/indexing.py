"""
LlamaIndex索引模块: 处理文档索引和结构化数据检索
利用LlamaIndex在分层索引和上下文感知检索方面的优势
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
    """获取配置了块大小的LlamaIndex节点解析器"""
    chunk_size = settings.LLAMAINDEX_CHUNK_SIZE
    chunk_overlap = settings.LLAMAINDEX_CHUNK_OVERLAP
    
    return SimpleNodeParser.from_defaults(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

def get_milvus_vector_store(collection_name: Optional[str] = None):
    """获取LlamaIndex使用的Milvus向量存储"""
    collection = collection_name or settings.MILVUS_COLLECTION
    
    # 连接到Milvus
    return MilvusVectorStore(
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
        collection_name=collection,
        dim=1536  # OpenAI嵌入的维度
    )

def create_document_index(
    documents: List[Dict[str, Any]],
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None
) -> VectorStoreIndex:
    """
    从文档创建LlamaIndex
    
    参数:
        documents: 文档字典列表，包含'content'和'metadata'键
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        
    返回:
        LlamaIndex向量存储索引
    """
    # 转换为LlamaIndex文档对象
    llamaindex_docs = []
    for doc in documents:
        llamaindex_docs.append(
            Document(
                text=doc.get("content", ""),
                metadata=doc.get("metadata", {})
            )
        )
    
    # 创建解析器
    parser = get_node_parser()
    nodes = parser.get_nodes_from_documents(llamaindex_docs)
    
    # 创建向量存储
    vector_store = get_milvus_vector_store(collection_name)
    
    # 创建索引
    index = VectorStoreIndex(
        nodes=nodes,
        vector_store=vector_store
    )
    
    # 如果提供了目录，则持久化索引
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
    加载现有索引或创建新索引
    
    参数:
        documents: 如果创建新索引，则为可选的要索引的文档
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        
    返回:
        LlamaIndex向量存储索引
    """
    # 尝试加载现有索引
    if persist_dir and os.path.exists(persist_dir):
        try:
            # 创建向量存储
            vector_store = get_milvus_vector_store(collection_name)
            
            # 创建存储上下文
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=persist_dir
            )
            
            # 加载索引
            return load_index_from_storage(storage_context)
        
        except Exception as e:
            print(f"加载索引时出错: {e}")
            # 回退到创建新索引
    
    # 创建新索引
    if documents:
        return create_document_index(documents, collection_name, persist_dir)
    else:
        raise ValueError("如果没有找到现有索引，则必须提供文档")

def index_document(
    document: Dict[str, Any],
    index: Optional[VectorStoreIndex] = None,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None
) -> VectorStoreIndex:
    """
    索引单个文档，更新现有索引或创建新索引
    
    参数:
        document: 文档字典，包含'content'和'metadata'键
        index: 可选的要更新的现有索引
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        
    返回:
        更新后的LlamaIndex向量存储索引
    """
    # 创建LlamaIndex文档
    llamaindex_doc = Document(
        text=document.get("content", ""),
        metadata=document.get("metadata", {})
    )
    
    # 创建解析器并提取节点
    parser = get_node_parser()
    nodes = parser.get_nodes_from_documents([llamaindex_doc])
    
    # 如果索引存在，插入节点
    if index:
        for node in nodes:
            index.insert(node)
        
        # 如果提供了目录，则持久化
        if persist_dir:
            index.storage_context.persist(persist_dir=persist_dir)
        
        return index
    
    # 否则创建新索引
    return create_document_index([document], collection_name, persist_dir)

def index_directory(
    directory_path: str,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    file_extns: Optional[List[str]] = None
) -> VectorStoreIndex:
    """
    索引目录中的所有文档
    
    参数:
        directory_path: 包含文档的目录路径
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        file_extns: 可选的要包含的文件扩展名列表
        
    返回:
        LlamaIndex向量存储索引
    """
    # 如果未提供，则使用默认文件扩展名
    if file_extns is None:
        file_extns = [".txt", ".pdf", ".md", ".docx", ".csv", ".html"]
    
    # 从目录加载文档
    reader = SimpleDirectoryReader(
        input_dir=directory_path,
        required_exts=file_extns
    )
    documents = reader.load_data()
    
    # 创建解析器
    parser = get_node_parser()
    nodes = parser.get_nodes_from_documents(documents)
    
    # 创建向量存储
    vector_store = get_milvus_vector_store(collection_name)
    
    # 创建索引
    index = VectorStoreIndex(
        nodes=nodes,
        vector_store=vector_store
    )
    
    # 如果提供了目录，则持久化索引
    if persist_dir:
        os.makedirs(persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=persist_dir)
    
    return index
