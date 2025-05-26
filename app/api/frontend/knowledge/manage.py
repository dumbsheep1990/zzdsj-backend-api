"""
知识库管理API模块: 提供知识库及其文档的CRUD操作
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime

from app.utils.database import get_db
# 导入统一知识库服务
from app.services.unified_knowledge_service import get_unified_knowledge_service
from app.schemas.knowledge import (
    KnowledgeBase as KnowledgeBaseSchema,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseWithStats,
    Document as DocumentSchema,
    DocumentCreate,
    DocumentUpdate,
    KnowledgeBaseStats,
    DocumentListResponse
)
from app.frameworks.llamaindex import KnowledgeBaseProcessor
from app.utils.object_storage import upload_file, get_file_url
from app.api.frontend.dependencies import ResponseFormatter

router = APIRouter()

@router.get("/", response_model=List[KnowledgeBaseWithStats])
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
    service = get_unified_knowledge_service(db)
    knowledge_bases = await service.get_knowledge_bases(skip, limit, is_active, search)
    return ResponseFormatter.format_success(knowledge_bases)

@router.post("/", response_model=KnowledgeBaseSchema, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """
    创建新知识库。
    """
    service = get_unified_knowledge_service(db)
    db_knowledge_base = await service.create_knowledge_base(knowledge_base)
    return ResponseFormatter.format_success(db_knowledge_base)

@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseWithStats)
async def get_knowledge_base(
    knowledge_base_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定知识库的详细信息及统计数据。
    """
    service = get_unified_knowledge_service(db)
    kb = await service.get_knowledge_base(knowledge_base_id)
    
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库未找到")
    
    return ResponseFormatter.format_success(kb)

@router.get("/{knowledge_base_id}/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(
    knowledge_base_id: str,
    db: Session = Depends(get_db)
):
    """
    获取知识库的详细统计信息。
    """
    service = get_unified_knowledge_service(db)
    stats = await service.get_knowledge_base_stats(knowledge_base_id)
    
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库未找到")
    
    return ResponseFormatter.format_success(stats)

@router.put("/{knowledge_base_id}", response_model=KnowledgeBaseSchema)
async def update_knowledge_base(
    knowledge_base_id: str,
    knowledge_base: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """
    更新知识库信息。
    """
    service = get_unified_knowledge_service(db)
    db_knowledge_base = await service.update_knowledge_base(knowledge_base_id, knowledge_base)
    return ResponseFormatter.format_success(db_knowledge_base)

@router.delete("/{knowledge_base_id}")
async def delete_knowledge_base(
    knowledge_base_id: str,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除知识库及其所有文档。
    permanent参数决定是物理删除还是逻辑删除。
    """
    service = get_unified_knowledge_service(db)
    result = await service.delete_knowledge_base(knowledge_base_id, permanent)
    return ResponseFormatter.format_success(result)

# 文档管理端点
@router.get("/{knowledge_base_id}/documents", response_model=DocumentListResponse)
async def get_documents(
    knowledge_base_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取知识库中的文档列表。
    """
    service = get_unified_knowledge_service(db)
    documents = await service.get_documents(knowledge_base_id, skip, limit, status, search)
    return ResponseFormatter.format_success({"documents": documents, "total": len(documents)})

@router.post("/{knowledge_base_id}/documents", response_model=DocumentSchema)
async def create_document(
    knowledge_base_id: str,
    title: str = Form(...),
    content: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    language: Optional[str] = Form("zh"),
    doc_type: Optional[str] = Form("text"),
    file: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    为知识库添加新文档，支持文本内容或文件上传。
    """
    service = get_unified_knowledge_service(db)
    document_data = DocumentCreate(
        title=title,
        content=content,
        metadata=json.loads(metadata) if metadata else {},
        language=language,
        doc_type=doc_type,
        file_url=None  # 初始为空，由服务层处理文件上传
    )
    document = await service.create_document(knowledge_base_id, document_data, file)
    return ResponseFormatter.format_success(document)

@router.get("/{knowledge_base_id}/documents/{document_id}", response_model=DocumentSchema)
async def get_document(
    knowledge_base_id: str,
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    通过ID获取文档。
    """
    service = get_unified_knowledge_service(db)
    document = await service.get_document_by_id(document_id, knowledge_base_id)
    
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到文档")
    
    return ResponseFormatter.format_success(document)

@router.delete("/{knowledge_base_id}/documents/{document_id}")
async def delete_document(
    knowledge_base_id: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    从知识库中删除文档。
    """
    service = get_unified_knowledge_service(db)
    success = await service.delete_document(document_id, knowledge_base_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="删除文档失败")
    
    return ResponseFormatter.format_success(None, message="文档删除成功")

async def remove_document_from_agno(knowledge_base_id: str, document_id: str):
    """从Agno知识库中删除文档"""
    try:
        # 初始化Agno KB处理器
        kb_processor = KnowledgeBaseProcessor(
            kb_id=knowledge_base_id
        )
        
        # 从Agno中删除文档
        await kb_processor.remove_document(document_id=document_id)
        
        print(f"成功从Agno知识库 {knowledge_base_id} 中删除文档 {document_id}")
    except Exception as e:
        print(f"从Agno中删除文档时出错: {e}")
        # 在生产系统中，我们可能希望：
        # 1. 将错误记录到监控系统中
        # 2. 添加到重试队列中
        # 3. 更新数据库中的文档状态 