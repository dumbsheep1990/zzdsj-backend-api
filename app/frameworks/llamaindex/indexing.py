"""
LlamaIndex索引模块: 处理文档索引和结构化数据检索
利用LlamaIndex在分层索引和上下文感知检索方面的优势
支持ES与Milvus双引擎、动态文档切分
"""

from typing import List, Dict, Any, Optional, Union, Callable
from pathlib import Path
import os
import time
import logging
import uuid
from datetime import datetime

from llama_index.core import (
    Document, 
    VectorStoreIndex, 
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage
)
from llama_index.core.node_parser import (
    SimpleNodeParser,
    SentenceSplitter,
    TokenTextSplitter
)
from llama_index.vector_stores.milvus import MilvusVectorStore
from app.config import settings
from app.frameworks.llamaindex.elasticsearch_store import get_elasticsearch_store
from app.frameworks.llamaindex.document_processor import (
    get_document_processor,
    SplitterType,
    ProcessingStatus,
    DocumentProcessor
)

logger = logging.getLogger(__name__)

def get_node_parser(
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
):
    """
    获取配置的LlamaIndex节点解析器
    
    参数:
        splitter_type: 切分器类型，可选，默认使用配置中的值
        chunk_size: 块大小，可选，默认使用配置中的值
        chunk_overlap: 块重叠，可选，默认使用配置中的值
    
    返回:
        配置好的节点解析器
    """
    # 使用传入参数或配置值
    _chunk_size = chunk_size or settings.DOCUMENT_CHUNK_SIZE
    _chunk_overlap = chunk_overlap or settings.DOCUMENT_CHUNK_OVERLAP
    _splitter_type = splitter_type or settings.DOCUMENT_SPLITTER_TYPE
    
    # 根据类型选择解析器
    if _splitter_type == "sentence":
        return SentenceSplitter(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap
        )
    elif _splitter_type == "token":
        return TokenTextSplitter(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap
        )
    else:
        # 默认使用简单节点解析器
        return SimpleNodeParser.from_defaults(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap
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

def get_vector_store(store_type: Optional[str] = None, **kwargs):
    """
    获取向量存储，支持ES和Milvus
    
    参数:
        store_type: 存储类型，'elasticsearch'或'milvus'，默认使用配置
        **kwargs: 存储特定参数
    
    返回:
        配置好的向量存储实例
    """
    # 使用传入类型或配置值
    _store_type = store_type or settings.LLAMAINDEX_DEFAULT_STORE
    
    if _store_type == "elasticsearch":
        index_name = kwargs.get("index_name", None)
        recreate_index = kwargs.get("recreate_index", False)
        return get_elasticsearch_store(index_name, recreate_index)
    else:
        collection_name = kwargs.get("collection_name", None)
        return get_milvus_vector_store(collection_name)

def create_document_index(
    documents: List[Dict[str, Any]],
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    store_type: Optional[str] = None,
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> VectorStoreIndex:
    """
    从文档创建LlamaIndex
    
    参数:
        documents: 文档字典列表，包含'content'和'metadata'键
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        store_type: 存储类型，'elasticsearch'或'milvus'
        splitter_type: 文档切分器类型
        chunk_size: 文档块大小
        chunk_overlap: 文档块重叠大小
        
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
    parser = get_node_parser(splitter_type, chunk_size, chunk_overlap)
    nodes = parser.get_nodes_from_documents(llamaindex_docs)
    
    # 创建向量存储
    if store_type == "elasticsearch" or (not store_type and settings.LLAMAINDEX_DEFAULT_STORE == "elasticsearch"):
        vector_store = get_elasticsearch_store()
    else:
        vector_store = get_milvus_vector_store(collection_name)
    
    # 创建存储上下文
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )
    
    # 创建索引
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context
    )
    
    # 如果提供了目录，则持久化索引
    if persist_dir:
        os.makedirs(persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=persist_dir)
    
    return index

def load_or_create_index(
    documents: Optional[List[Dict[str, Any]]] = None,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    store_type: Optional[str] = None
) -> VectorStoreIndex:
    """
    加载现有索引或创建新索引
    
    参数:
        documents: 如果创建新索引，则为可选的要索引的文档
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        store_type: 存储类型，'elasticsearch'或'milvus'
        
    返回:
        LlamaIndex向量存储索引
    """
    # 选择向量存储
    if store_type == "elasticsearch" or (not store_type and settings.LLAMAINDEX_DEFAULT_STORE == "elasticsearch"):
        vector_store = get_elasticsearch_store()
    else:
        vector_store = get_milvus_vector_store(collection_name)
        
    # 尝试加载现有索引
    if persist_dir and os.path.exists(persist_dir):
        try:
            # 创建存储上下文
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=persist_dir
            )
            
            # 加载索引
            return load_index_from_storage(storage_context)
        
        except Exception as e:
            logger.error(f"加载索引时出错: {e}")
            # 回退到创建新索引
    
    # 创建新索引
    if documents:
        return create_document_index(documents, collection_name, persist_dir, store_type)
    else:
        raise ValueError("如果没有找到现有索引，则必须提供文档")

def index_document(
    document: Dict[str, Any],
    index: Optional[VectorStoreIndex] = None,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    store_type: Optional[str] = None,
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> VectorStoreIndex:
    """
    索引单个文档，更新现有索引或创建新索引
    
    参数:
        document: 文档字典，包含'content'和'metadata'键
        index: 可选的要更新的现有索引
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        store_type: 存储类型，'elasticsearch'或'milvus'
        splitter_type: 文档切分器类型
        chunk_size: 文档块大小
        chunk_overlap: 文档块重叠大小
        
    返回:
        更新后的LlamaIndex向量存储索引
    """
    # 创建LlamaIndex文档
    llamaindex_doc = Document(
        text=document.get("content", ""),
        metadata=document.get("metadata", {})
    )
    
    # 创建解析器并提取节点
    parser = get_node_parser(splitter_type, chunk_size, chunk_overlap)
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
    return create_document_index(
        [document], 
        collection_name, 
        persist_dir, 
        store_type,
        splitter_type,
        chunk_size,
        chunk_overlap
    )

def index_directory(
    directory_path: str,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    file_extns: Optional[List[str]] = None,
    store_type: Optional[str] = None,
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> VectorStoreIndex:
    """
    索引目录中的所有文档
    
    参数:
        directory_path: 包含文档的目录路径
        collection_name: 可选的Milvus集合名称
        persist_dir: 可选的索引持久化目录
        file_extns: 可选的要包含的文件扩展名列表
        store_type: 存储类型，'elasticsearch'或'milvus'
        splitter_type: 文档切分器类型
        chunk_size: 文档块大小
        chunk_overlap: 文档块重叠大小
        
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
    parser = get_node_parser(splitter_type, chunk_size, chunk_overlap)
    nodes = parser.get_nodes_from_documents(documents)
    
    # 创建向量存储
    if store_type == "elasticsearch" or (not store_type and settings.LLAMAINDEX_DEFAULT_STORE == "elasticsearch"):
        vector_store = get_elasticsearch_store()
    else:
        vector_store = get_milvus_vector_store(collection_name)
    
    # 创建存储上下文
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )
    
    # 创建索引
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context
    )
    
    # 如果提供了目录，则持久化索引
    if persist_dir:
        os.makedirs(persist_dir, exist_ok=True)
        index.storage_context.persist(persist_dir=persist_dir)
    
    return index

def process_document_async(
    source_path: str,
    task_id: Optional[str] = None,
    callback: Optional[Callable] = None,
    splitter_type: Optional[Union[str, SplitterType]] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    使用异步文档处理器处理文档
    
    参数:
        source_path: 文档路径或URL
        task_id: 可选的任务ID
        callback: 可选的回调函数
        splitter_type: 文档切分器类型
        chunk_size: 文档块大小
        chunk_overlap: 文档块重叠大小
        metadata: 要添加到文档的元数据
        **kwargs: 其他处理参数
        
    返回:
        任务ID
    """
    # 获取处理器实例
    processor = get_document_processor()
    
    # 如果传入的splitter_type是字符串，转换为枚举
    if isinstance(splitter_type, str):
        try:
            splitter_type = SplitterType(splitter_type)
        except ValueError:
            splitter_type = SplitterType(settings.DOCUMENT_SPLITTER_TYPE)
    
    # 添加元数据
    if metadata:
        kwargs["metadata"] = metadata
    
    # 启动异步处理
    task_id = processor.process_document(
        source_path=source_path,
        task_id=task_id,
        callback=callback,
        splitter_type=splitter_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )
    
    return task_id

def get_document_processing_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取文档处理状态
    
    参数:
        task_id: 任务ID
        
    返回:
        任务状态信息或None
    """
    processor = get_document_processor()
    return processor.get_task_status(task_id)
