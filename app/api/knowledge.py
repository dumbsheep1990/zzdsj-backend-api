from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime

from app.utils.database import get_db
from app.services.knowledge_service import KnowledgeService
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
    service = KnowledgeService(db)
    knowledge_bases = await service.get_knowledge_bases(skip, limit, is_active, search)
    return knowledge_bases

@router.post("/", response_model=KnowledgeBaseSchema, status_code=201)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """
    创建新知识库。
    """
    service = KnowledgeService(db)
    db_knowledge_base = await service.create_knowledge_base(knowledge_base)
    return db_knowledge_base

@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseWithStats)
async def get_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定知识库的详细信息及统计数据。
    """
    service = KnowledgeService(db)
    kb = await service.get_knowledge_base_by_id(knowledge_base_id)
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库未找到")
    
    return kb

@router.get("/{knowledge_base_id}/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats(
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    获取知识库的详细统计信息。
    """
    service = KnowledgeService(db)
    stats = await service.get_knowledge_base_stats(knowledge_base_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="知识库未找到")
    
    return stats

@router.put("/{knowledge_base_id}", response_model=KnowledgeBaseSchema)
async def update_knowledge_base(
    knowledge_base_id: int,
    knowledge_base: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """
    更新知识库信息。
    """
    service = KnowledgeService(db)
    db_knowledge_base = await service.update_knowledge_base(knowledge_base_id, knowledge_base)
    return db_knowledge_base

@router.delete("/{knowledge_base_id}")
async def delete_knowledge_base(
    knowledge_base_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除知识库及其所有文档。
    permanent参数决定是物理删除还是逻辑删除。
    """
    service = KnowledgeService(db)
    result = await service.delete_knowledge_base(knowledge_base_id, permanent)
    return {"message": result["message"]}

# 文档管理端点
@router.get("/{knowledge_base_id}/documents", response_model=DocumentListResponse)
async def get_documents(
    knowledge_base_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取知识库中的文档列表。
    """
    service = KnowledgeService(db)
    documents = await service.get_documents(knowledge_base_id, skip, limit, status, search)
    return {"documents": documents, "total": len(documents)}

@router.post("/{knowledge_base_id}/documents", response_model=DocumentSchema)
async def create_document(
    knowledge_base_id: int,
    title: str = Form(...),
    content: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    language: Optional[str] = Form("en"),
    doc_type: Optional[str] = Form("text"),
    file: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    为知识库添加新文档，支持文本内容或文件上传。
    """
    service = KnowledgeService(db)
    document_data = DocumentCreate(
        title=title,
        content=content,
        metadata=json.loads(metadata) if metadata else {},
        language=language,
        doc_type=doc_type,
        file_url=None  # 初始为空，由服务层处理文件上传
    )
    document = await service.create_document(knowledge_base_id, document_data, file, background_tasks)
    return document

@router.get("/{knowledge_base_id}/documents/{document_id}", response_model=DocumentSchema)
async def get_document(
    knowledge_base_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取文档。
    """
    service = KnowledgeService(db)
    document = await service.get_document_by_id(knowledge_base_id, document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail="未找到文档")
    
    return document

@router.delete("/{knowledge_base_id}/documents/{document_id}")
async def delete_document(
    knowledge_base_id: int,
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    从知识库中删除文档。
    """
    service = KnowledgeService(db)
    success = await service.delete_document(knowledge_base_id, document_id, background_tasks)
    
    if not success:
        raise HTTPException(status_code=404, detail="删除文档失败")
    
    return {"message": "文档删除成功"}

async def remove_document_from_agno(knowledge_base_id: int, document_id: int):
    """从Agno知识库中删除文档"""
    try:
        # 初始化Agno KB处理器
        kb_processor = KnowledgeBaseProcessor(
            kb_id=str(knowledge_base_id)
        )
        
        # 从Agno中删除文档
        await kb_processor.remove_document(document_id=str(document_id))
        
        print(f"成功从Agno知识库 {knowledge_base_id} 中删除文档 {document_id}")
    except Exception as e:
        print(f"从Agno中删除文档时出错: {e}")
        # 在生产系统中，我们可能希望：
        # 1. 将错误记录到监控系统中
        # 2. 添加到重试队列中
        # 3. 更新数据库中的文档状态


