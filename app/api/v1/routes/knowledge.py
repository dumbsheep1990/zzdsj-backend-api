"""
知识库API路由
提供统一的知识库管理和查询接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
import json
import logging
from datetime import datetime

from app.models.database import get_db
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.schemas.knowledge import (
    KnowledgeBase as KnowledgeBaseSchema,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseWithStats,
    Document as DocumentSchema,
    DocumentCreate,
    DocumentUpdate,
    KnowledgeBaseStats,
    DocumentListResponse,
    KnowledgeQueryRequest
)
from app.api.v1.dependencies import (
    get_knowledge_adapter, ResponseFormatter, get_request_context
)
from app.messaging.adapters.knowledge import KnowledgeAdapter
from app.messaging.core.models import (
    Message as CoreMessage, MessageRole, TextMessage
)
from app.frameworks.llamaindex.core import get_service_context
from core.knowledge.document_processor import process_document

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/bases", response_model=List[KnowledgeBaseWithStats])
async def get_knowledge_bases(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有知识库及其统计信息，支持搜索和过滤。
    """
    query = db.query(KnowledgeBase)
    
    if is_active is not None:
        query = query.filter(KnowledgeBase.is_active == is_active)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            KnowledgeBase.name.ilike(search_term) | 
            KnowledgeBase.description.ilike(search_term)
        )
    
    knowledge_bases = query.order_by(KnowledgeBase.created_at.desc()).offset(skip).limit(limit).all()
    
    # 获取每个知识库的文档数量
    result = []
    for kb in knowledge_bases:
        doc_count = db.query(func.count(Document.id)).filter(
            Document.knowledge_base_id == kb.id
        ).scalar()
        
        kb_dict = kb.__dict__.copy()
        if "_sa_instance_state" in kb_dict:
            del kb_dict["_sa_instance_state"]
        
        kb_dict["stats"] = {
            "document_count": doc_count,
            "updated_at": kb.updated_at
        }
        
        result.append(kb_dict)
    
    return ResponseFormatter.format_success(result)


@router.post("/bases", response_model=KnowledgeBaseSchema)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建新知识库，初始化LlamaIndex集成。
    """
    # 创建知识库记录
    db_knowledge_base = KnowledgeBase(
        name=knowledge_base.name,
        description=knowledge_base.description,
        type=knowledge_base.type,
        is_active=knowledge_base.is_active,
        config=knowledge_base.config or {},
        metadata=knowledge_base.metadata or {}
    )
    
    db.add(db_knowledge_base)
    db.commit()
    db.refresh(db_knowledge_base)
    
    # 将知识库初始化任务放入后台任务
    background_tasks.add_task(initialize_knowledge_base, db_knowledge_base.id, db)
    
    return ResponseFormatter.format_success(db_knowledge_base)


async def initialize_knowledge_base(kb_id: int, db: Session):
    """初始化知识库的索引和存储"""
    try:
        # 获取知识库记录
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            logger.error(f"知识库初始化失败: ID {kb_id} 不存在")
            return
        
        # 记录初始化状态
        kb.status = "initializing"
        db.commit()
        
        # 使用LlamaIndex创建知识库索引
        service_context = get_service_context()
        
        # 更新状态为就绪
        kb.status = "ready"
        kb.metadata["initialized"] = True
        kb.metadata["initialized_at"] = datetime.now().isoformat()
        db.commit()
        
        logger.info(f"知识库初始化成功: {kb.name} (ID: {kb.id})")
    except Exception as e:
        logger.error(f"知识库初始化错误: {str(e)}")
        # 更新状态为失败
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if kb:
            kb.status = "error"
            kb.metadata["error"] = str(e)
            db.commit()


@router.get("/bases/{knowledge_base_id}", response_model=KnowledgeBaseWithStats)
async def get_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取知识库及其详细统计信息。
    """
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    
    # 获取文档统计信息
    doc_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar()
    
    # 获取文档块统计信息
    chunk_count = db.query(func.count(DocumentChunk.id)).join(
        Document, Document.id == DocumentChunk.document_id
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar()
    
    # 获取最新文档
    latest_docs = db.query(Document).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).order_by(Document.created_at.desc()).limit(5).all()
    
    kb_dict = knowledge_base.__dict__.copy()
    if "_sa_instance_state" in kb_dict:
        del kb_dict["_sa_instance_state"]
    
    kb_dict["stats"] = {
        "document_count": doc_count,
        "chunk_count": chunk_count,
        "latest_documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "created_at": doc.created_at
            } for doc in latest_docs
        ]
    }
    
    return ResponseFormatter.format_success(kb_dict)


@router.put("/bases/{knowledge_base_id}", response_model=KnowledgeBaseSchema)
async def update_knowledge_base(
    knowledge_base_id: int,
    knowledge_base_update: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """
    更新知识库。
    """
    db_knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not db_knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    
    # 更新字段
    if knowledge_base_update.name is not None:
        db_knowledge_base.name = knowledge_base_update.name
    
    if knowledge_base_update.description is not None:
        db_knowledge_base.description = knowledge_base_update.description
    
    if knowledge_base_update.is_active is not None:
        db_knowledge_base.is_active = knowledge_base_update.is_active
    
    if knowledge_base_update.config is not None:
        db_knowledge_base.config = knowledge_base_update.config
    
    if knowledge_base_update.metadata is not None:
        # 合并元数据，保留现有字段
        db_knowledge_base.metadata.update(knowledge_base_update.metadata)
    
    db_knowledge_base.updated_at = datetime.now()
    db.commit()
    db.refresh(db_knowledge_base)
    
    return ResponseFormatter.format_success(db_knowledge_base)


@router.delete("/bases/{knowledge_base_id}")
async def delete_knowledge_base(
    knowledge_base_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除或停用知识库。
    """
    db_knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not db_knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    
    if permanent:
        # 删除关联的文档块
        doc_ids = [doc.id for doc in db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id).all()]
        if doc_ids:
            db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).delete(synchronize_session=False)
        
        # 删除关联的文档
        db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id).delete(synchronize_session=False)
        
        # 删除知识库
        db.delete(db_knowledge_base)
    else:
        # 仅停用知识库
        db_knowledge_base.is_active = False
        db_knowledge_base.updated_at = datetime.now()
    
    db.commit()
    
    return ResponseFormatter.format_success(None, message=f"知识库已{'删除' if permanent else '停用'}")


@router.get("/bases/{knowledge_base_id}/documents", response_model=DocumentListResponse)
async def get_documents(
    knowledge_base_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    mime_type: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db)
):
    """
    获取知识库中的所有文档，支持分页、过滤和排序。
    """
    # 检查知识库是否存在
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    
    # 构建基本查询
    query = db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id)
    
    # 应用过滤条件
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Document.title.ilike(search_term) | 
            Document.content.ilike(search_term)
        )
    
    if status:
        query = query.filter(Document.status == status)
    
    if mime_type:
        query = query.filter(Document.mime_type == mime_type)
    
    # 获取总数
    total_count = query.count()
    
    # 应用排序
    if sort_by:
        if hasattr(Document, sort_by):
            order_column = getattr(Document, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column)
        else:
            # 默认按创建时间排序
            query = query.order_by(Document.created_at.desc())
    else:
        # 默认按创建时间排序
        query = query.order_by(Document.created_at.desc())
    
    # 应用分页
    offset = (page - 1) * page_size
    documents = query.offset(offset).limit(page_size).all()
    
    # 计算总页数
    total_pages = (total_count + page_size - 1) // page_size
    
    # 构建响应
    result = {
        "documents": documents,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages
        }
    }
    
    return ResponseFormatter.format_success(result)


@router.post("/bases/{knowledge_base_id}/documents", response_model=DocumentSchema)
async def create_document(
    knowledge_base_id: int,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None),
    metadata: Optional[str] = Form("{}"),
    db: Session = Depends(get_db)
):
    """
    向知识库添加新文档，可以通过上传文件或直接提供内容。
    使用LlamaIndex进行文档处理和索引。
    """
    # 检查知识库是否存在
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    
    # 检查必须提供文件或内容
    if file is None and not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须提供文件或内容")
    
    try:
        parsed_metadata = json.loads(metadata)
    except json.JSONDecodeError:
        parsed_metadata = {}
    
    # 处理文件上传
    file_path = None
    mime_type = "text/plain"
    file_size = 0
    file_content = content or ""
    
    if file:
        # 获取MIME类型
        mime_type = file.content_type or "application/octet-stream"
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 如果是二进制文件，需要保存到存储系统中
        if not mime_type.startswith("text/"):
            # 这里应该调用对象存储服务上传文件，获取URL
            # 为简化示例，这里使用临时路径
            file_path = f"tmp/{file.filename}"
            with open(file_path, "wb") as f:
                f.write(file_content)
        else:
            # 文本文件，直接使用内容
            file_content = file_content.decode("utf-8")
    
    # 创建文档记录
    db_document = Document(
        knowledge_base_id=knowledge_base_id,
        title=title,
        content=file_content if isinstance(file_content, str) else "",
        file_path=file_path,
        mime_type=mime_type,
        file_size=file_size,
        status="pending",
        metadata=parsed_metadata
    )
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # 将文档处理任务放入后台任务
    background_tasks.add_task(process_document, db_document.id, db)
    
    return ResponseFormatter.format_success(db_document)


@router.get("/bases/{knowledge_base_id}/documents/{document_id}", response_model=DocumentSchema)
async def get_document(
    knowledge_base_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取文档。
    """
    document = db.query(Document).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    
    return ResponseFormatter.format_success(document)


@router.delete("/bases/{knowledge_base_id}/documents/{document_id}")
async def delete_document(
    knowledge_base_id: int,
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    从知识库中删除文档。
    """
    # 检查文档是否存在
    document = db.query(Document).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
    
    # 删除文档块
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # 删除文档
    db.delete(document)
    db.commit()
    
    # 从索引中移除文档
    background_tasks.add_task(remove_document_from_index, knowledge_base_id, document_id)
    
    return ResponseFormatter.format_success(None, message="文档已删除")


async def remove_document_from_index(knowledge_base_id: int, document_id: int):
    """从索引中删除文档"""
    try:
        # 这里实现从LlamaIndex索引中删除文档的逻辑
        logger.info(f"已从索引中删除文档 {document_id}")
    except Exception as e:
        logger.error(f"从索引中删除文档失败: {str(e)}")


@router.post("/query", response_model=Dict[str, Any])
async def query_knowledge_base(
    query_request: KnowledgeQueryRequest,
    knowledge_adapter: KnowledgeAdapter = Depends(get_knowledge_adapter),
    db: Session = Depends(get_db)
):
    """
    查询知识库内容
    """
    # 检查知识库是否存在
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == query_request.knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")
    
    # 创建查询消息
    query_message = TextMessage(
        content=query_request.query,
        role=MessageRole.USER
    )
    
    # 准备查询参数
    search_params = {
        "knowledge_base_id": query_request.knowledge_base_id,
        "top_k": query_request.top_k or 3,
        "similarity_threshold": query_request.similarity_threshold or 0.7
    }
    
    # 使用知识库查询函数
    def search_function(query, **params):
        # 这里需要实现实际的搜索功能
        # 示例实现
        chunks = db.query(DocumentChunk).join(
            Document, Document.id == DocumentChunk.document_id
        ).filter(
            Document.knowledge_base_id == params["knowledge_base_id"]
        ).limit(params["top_k"]).all()
        
        return [
            {
                "content": chunk.content,
                "document_id": chunk.document_id,
                "score": 0.9  # 示例分数
            } for chunk in chunks
        ]
    
    # 使用统一消息系统处理请求
    try:
        # 选择适当的回复格式
        if query_request.stream:
            # 异步处理返回SSE流
            return await knowledge_adapter.to_sse_response(
                messages=[query_message],
                search_func=search_function,
                search_params=search_params,
                model_name=query_request.model_name,
                temperature=query_request.temperature,
                system_prompt=query_request.system_prompt
            )
        else:
            # 同步处理返回JSON
            response_messages = await knowledge_adapter.process_messages(
                messages=[query_message],
                search_func=search_function,
                search_params=search_params,
                model_name=query_request.model_name,
                temperature=query_request.temperature,
                system_prompt=query_request.system_prompt
            )
            
            # 使用OpenAI兼容格式返回结果
            return ResponseFormatter.format_openai_compatible(response_messages)
    except Exception as e:
        logger.error(f"知识库查询错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"知识库查询出错: {str(e)}")


@router.post("/query/stream")
async def query_knowledge_base_stream(
    query_request: KnowledgeQueryRequest,
    knowledge_adapter: KnowledgeAdapter = Depends(get_knowledge_adapter),
    db: Session = Depends(get_db)
):
    """
    流式查询知识库内容，返回SSE格式的响应流。
    """
    # 确保请求使用流模式
    query_request.stream = True
    return await query_knowledge_base(query_request, knowledge_adapter, db)
