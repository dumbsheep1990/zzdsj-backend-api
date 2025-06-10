"""
Agno索引模块: 处理文档索引和结构化数据检索
基于Agno框架实现，利用Agno在知识库管理和向量检索方面的优势
支持多种向量数据库和动态文档处理
"""

from typing import List, Dict, Any, Optional, Union, Callable
from pathlib import Path
import os
import time
import logging
import uuid
from datetime import datetime

from app.config import settings
from app.frameworks.agno.config import get_agno_config
from app.frameworks.agno.knowledge_base import AgnoKnowledgeBase, KnowledgeBaseProcessor
from app.tools.base.document_chunking import (
    get_chunking_tool, 
    ChunkingConfig, 
    DocumentChunk,
    ChunkingResult
)

logger = logging.getLogger(__name__)

def get_node_parser(
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
):
    """
    获取配置的Agno文档切分器，对应LlamaIndex的get_node_parser
    
    参数:
        splitter_type: 切分器类型
        chunk_size: 块大小
        chunk_overlap: 块重叠
    
    返回:
        配置好的切分配置
    """
    config = get_agno_config()
    
    # 使用传入参数或配置值
    _chunk_size = chunk_size or config.kb_settings.get("chunk_size", 1000)
    _chunk_overlap = chunk_overlap or config.kb_settings.get("chunk_overlap", 200)
    _splitter_type = splitter_type or "sentence"
    
    # 创建Agno切分配置
    chunking_config = ChunkingConfig(
        strategy=_splitter_type,
        chunk_size=_chunk_size,
        chunk_overlap=_chunk_overlap,
        language="zh",
        preserve_structure=True,
        semantic_threshold=config.kb_settings.get("similarity_threshold", 0.7)
    )
    
    return chunking_config

def get_vector_store(store_type: Optional[str] = None, **kwargs):
    """
    获取Agno向量存储，对应LlamaIndex的get_vector_store
    
    参数:
        store_type: 存储类型
        **kwargs: 存储特定参数
    
    返回:
        配置好的向量存储实例
    """
    from app.frameworks.agno.vector_store import AgnoVectorStore
    
    config = get_agno_config()
    _store_type = store_type or "milvus"  # Agno默认使用milvus
    
    return AgnoVectorStore(
        store_type=_store_type,
        collection_name=kwargs.get("collection_name", "agno_default"),
        config=config.to_dict(),
        **kwargs
    )

def create_document_index(
    documents: List[Dict[str, Any]],
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    store_type: Optional[str] = None,
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> AgnoKnowledgeBase:
    """
    从文档创建Agno知识库索引，对应LlamaIndex的create_document_index
    
    参数:
        documents: 文档字典列表，包含'content'和'metadata'键
        collection_name: 可选的集合名称
        persist_dir: 可选的索引持久化目录
        store_type: 存储类型
        splitter_type: 文档切分器类型
        chunk_size: 文档块大小
        chunk_overlap: 文档块重叠大小
        
    返回:
        Agno知识库实例
    """
    try:
        # 创建知识库ID
        kb_id = collection_name or f"agno_kb_{int(time.time())}"
        
        # 创建切分配置
        chunking_config = get_node_parser(splitter_type, chunk_size, chunk_overlap)
        
        # 创建Agno知识库
        agno_kb = AgnoKnowledgeBase(
            kb_id=kb_id,
            name=f"Agno Knowledge Base {kb_id}",
            config={
                "chunking_strategy": chunking_config.strategy,
                "chunk_size": chunking_config.chunk_size,
                "chunk_overlap": chunking_config.chunk_overlap,
                "store_type": store_type or "milvus",
                "persist_dir": persist_dir
            }
        )
        
        # 批量添加文档
        if documents:
            result = agno_kb.add_documents(documents)
            logger.info(f"成功添加 {result.get('added_count', 0)} 个文档到知识库 {kb_id}")
        
        return agno_kb
        
    except Exception as e:
        logger.error(f"创建Agno文档索引时出错: {str(e)}")
        raise

def load_or_create_index(
    documents: Optional[List[Dict[str, Any]]] = None,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    store_type: Optional[str] = None
) -> AgnoKnowledgeBase:
    """
    加载现有索引或创建新索引，对应LlamaIndex的load_or_create_index
    
    参数:
        documents: 如果创建新索引，则为可选的要索引的文档
        collection_name: 可选的集合名称
        persist_dir: 可选的索引持久化目录
        store_type: 存储类型
        
    返回:
        Agno知识库实例
    """
    try:
        kb_id = collection_name or "default_agno_kb"
        
        # 尝试加载现有知识库
        from app.frameworks.agno.knowledge_base import get_knowledge_base
        
        try:
            existing_kb = get_knowledge_base(kb_id)
            if existing_kb:
                logger.info(f"加载现有Agno知识库: {kb_id}")
                return existing_kb.agno_kb
        except Exception as e:
            logger.debug(f"未找到现有知识库 {kb_id}: {str(e)}")
        
        # 创建新知识库
        if documents:
            logger.info(f"创建新Agno知识库: {kb_id}")
            return create_document_index(
                documents=documents,
                collection_name=kb_id,
                persist_dir=persist_dir,
                store_type=store_type
            )
        else:
            # 创建空知识库
            agno_kb = AgnoKnowledgeBase(
                kb_id=kb_id,
                name=f"Empty Agno KB {kb_id}",
                config={
                    "store_type": store_type or "milvus",
                    "persist_dir": persist_dir
                }
            )
            logger.info(f"创建空Agno知识库: {kb_id}")
            return agno_kb
            
    except Exception as e:
        logger.error(f"加载或创建Agno索引时出错: {str(e)}")
        raise

def index_document(
    document: Dict[str, Any],
    index: Optional[AgnoKnowledgeBase] = None,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    store_type: Optional[str] = None,
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> AgnoKnowledgeBase:
    """
    索引单个文档，对应LlamaIndex的index_document
    
    参数:
        document: 文档字典，包含'content'和'metadata'键
        index: 可选的要更新的现有索引
        collection_name: 可选的集合名称
        persist_dir: 可选的索引持久化目录
        store_type: 存储类型
        splitter_type: 文档切分器类型
        chunk_size: 文档块大小
        chunk_overlap: 文档块重叠大小
        
    返回:
        更新后的Agno知识库实例
    """
    try:
        # 如果有现有索引，添加文档到现有索引
        if index:
            result = index.add_document(document)
            logger.info(f"文档已添加到现有知识库，新增 {result.get('chunk_count', 0)} 个切片")
            return index
        
        # 否则创建新索引
        return create_document_index(
            documents=[document],
            collection_name=collection_name,
            persist_dir=persist_dir,
            store_type=store_type,
            splitter_type=splitter_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
    except Exception as e:
        logger.error(f"索引文档时出错: {str(e)}")
        raise

def index_directory(
    directory_path: str,
    collection_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    file_extns: Optional[List[str]] = None,
    store_type: Optional[str] = None,
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> AgnoKnowledgeBase:
    """
    索引目录中的所有文档，对应LlamaIndex的index_directory
    
    参数:
        directory_path: 包含文档的目录路径
        collection_name: 可选的集合名称
        persist_dir: 可选的索引持久化目录
        file_extns: 可选的要包含的文件扩展名列表
        store_type: 存储类型
        splitter_type: 文档切分器类型
        chunk_size: 文档块大小
        chunk_overlap: 文档块重叠大小
        
    返回:
        Agno知识库实例
    """
    try:
        # 默认支持的文件扩展名
        if file_extns is None:
            file_extns = [".txt", ".pdf", ".md", ".docx", ".csv", ".html", ".json"]
        
        # 扫描目录获取文件
        documents = []
        directory = Path(directory_path)
        
        if not directory.exists():
            raise ValueError(f"目录不存在: {directory_path}")
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in file_extns:
                try:
                    # 读取文件内容
                    content = ""
                    if file_path.suffix.lower() == ".txt":
                        content = file_path.read_text(encoding='utf-8')
                    elif file_path.suffix.lower() == ".md":
                        content = file_path.read_text(encoding='utf-8')
                    # 其他文件类型可以使用专门的解析器
                    
                    if content:
                        documents.append({
                            "content": content,
                            "metadata": {
                                "file_path": str(file_path),
                                "file_name": file_path.name,
                                "file_size": file_path.stat().st_size,
                                "file_extension": file_path.suffix,
                                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            }
                        })
                        
                except Exception as e:
                    logger.warning(f"跳过文件 {file_path}: {str(e)}")
        
        if not documents:
            raise ValueError(f"目录 {directory_path} 中未找到有效文档")
        
        # 创建索引
        agno_kb = create_document_index(
            documents=documents,
            collection_name=collection_name or f"dir_{directory.name}",
            persist_dir=persist_dir,
            store_type=store_type,
            splitter_type=splitter_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        logger.info(f"成功索引目录 {directory_path}，处理了 {len(documents)} 个文件")
        return agno_kb
        
    except Exception as e:
        logger.error(f"索引目录时出错: {str(e)}")
        raise

async def process_document_async(
    source_path: str,
    task_id: Optional[str] = None,
    callback: Optional[Callable] = None,
    splitter_type: Optional[str] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    异步处理文档，对应LlamaIndex的process_document_async
    
    参数:
        source_path: 源文档路径
        task_id: 任务ID
        callback: 进度回调函数
        splitter_type: 切分器类型
        chunk_size: 块大小
        chunk_overlap: 块重叠
        metadata: 文档元数据
        **kwargs: 其他参数
        
    返回:
        任务ID
    """
    import asyncio
    
    try:
        # 生成任务ID
        if not task_id:
            task_id = f"agno_task_{uuid.uuid4().hex[:8]}"
        
        # 定义异步处理函数
        async def process_task():
            try:
                # 更新进度: 开始处理
                if callback:
                    await callback(task_id, {"status": "processing", "progress": 0})
                
                # 读取文档
                file_path = Path(source_path)
                if not file_path.exists():
                    raise FileNotFoundError(f"文件不存在: {source_path}")
                
                content = file_path.read_text(encoding='utf-8')
                
                # 更新进度: 文档读取完成
                if callback:
                    await callback(task_id, {"status": "processing", "progress": 30})
                
                # 准备文档数据
                document = {
                    "content": content,
                    "metadata": {
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_size": file_path.stat().st_size,
                        "processed_at": datetime.now().isoformat(),
                        **(metadata or {})
                    }
                }
                
                # 更新进度: 开始索引
                if callback:
                    await callback(task_id, {"status": "indexing", "progress": 50})
                
                # 创建索引
                agno_kb = create_document_index(
                    documents=[document],
                    collection_name=kwargs.get("collection_name"),
                    splitter_type=splitter_type,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                # 更新进度: 完成
                if callback:
                    await callback(task_id, {
                        "status": "completed", 
                        "progress": 100,
                        "kb_id": agno_kb.kb_id,
                        "stats": agno_kb.get_stats()
                    })
                
                logger.info(f"异步文档处理完成: {task_id}")
                
            except Exception as e:
                logger.error(f"异步文档处理失败 {task_id}: {str(e)}")
                if callback:
                    await callback(task_id, {
                        "status": "failed", 
                        "progress": 0,
                        "error": str(e)
                    })
                raise
        
        # 启动异步任务
        asyncio.create_task(process_task())
        
        return task_id
        
    except Exception as e:
        logger.error(f"启动异步文档处理时出错: {str(e)}")
        raise

def get_document_processing_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取文档处理状态，对应LlamaIndex的get_document_processing_status
    
    参数:
        task_id: 任务ID
        
    返回:
        任务状态信息
    """
    try:
        # 这里可以实现任务状态跟踪
        # 简化实现，实际可以使用Redis或数据库存储状态
        return {
            "task_id": task_id,
            "status": "unknown",
            "message": "Agno异步任务状态跟踪功能待实现"
        }
        
    except Exception as e:
        logger.error(f"获取任务状态时出错: {str(e)}")
        return None

# 为了保持与LlamaIndex完全兼容，创建别名函数
create_llamaindex_index = create_document_index
load_llamaindex_index = load_or_create_index
get_milvus_vector_store = lambda collection_name=None: get_vector_store("milvus", collection_name=collection_name)
get_elasticsearch_vector_store = lambda index_name=None: get_vector_store("elasticsearch", index_name=index_name) 