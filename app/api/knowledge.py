from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
import os
import json
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
    DocumentListResponse
)
from app.frameworks.agno import KnowledgeBaseProcessor
from app.utils.object_storage import upload_file, get_file_url

router = APIRouter()

@router.get("/", response_model=List[KnowledgeBaseWithStats])
def get_knowledge_bases(
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
        query = query.filter(KnowledgeBase.name.ilike(f"%{search}%") | 
                           KnowledgeBase.description.ilike(f"%{search}%"))
    
    # 获取基本知识库数据
    knowledge_bases = query.offset(skip).limit(limit).all()
    
    # 用统计信息丰富数据
    result = []
    for kb in knowledge_bases:
        # 获取文档数量和文件类型分布
        doc_count = db.query(func.count(Document.id)).filter(
            Document.knowledge_base_id == kb.id
        ).scalar()
        
        # 获取文件类型分布
        file_types_query = db.query(
            Document.mime_type, 
            func.count(Document.id)
        ).filter(
            Document.knowledge_base_id == kb.id
        ).group_by(Document.mime_type).all()
        
        file_types = {mime_type: count for mime_type, count in file_types_query}
        
        # 获取令牌计数
        token_count = db.query(func.sum(DocumentChunk.token_count)).join(
            Document, DocumentChunk.document_id == Document.id
        ).filter(
            Document.knowledge_base_id == kb.id
        ).scalar() or 0
        
        # 创建增强模型
        kb_with_stats = KnowledgeBaseWithStats(
            **{k: getattr(kb, k) for k in kb.__table__.columns.keys()},
            document_count=doc_count,
            total_tokens=token_count,
            file_types=file_types
        )
        
        result.append(kb_with_stats)
    
    return result

@router.post("/", response_model=KnowledgeBaseSchema)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建新知识库，初始化Agno集成。
    """
    # 创建数据库记录
    db_knowledge_base = KnowledgeBase(
        name=knowledge_base.name,
        description=knowledge_base.description,
        settings=knowledge_base.settings,
        type=knowledge_base.type,
        embedding_model=knowledge_base.embedding_model
    )
    db.add(db_knowledge_base)
    db.commit()
    db.refresh(db_knowledge_base)
    
    # 在后台初始化Agno知识库
    background_tasks.add_task(
        initialize_agno_knowledge_base,
        db_knowledge_base.id,
        db
    )
    
    return db_knowledge_base

async def initialize_agno_knowledge_base(kb_id: int, db: Session):
    """为给定的数据库记录初始化Agno知识库"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        print(f"未找到知识库 {kb_id} 用于Agno初始化")
        return
    
    try:
        # 初始化Agno KB处理器
        kb_processor = KnowledgeBaseProcessor(
            kb_id=str(kb_id),
            name=kb.name
        )
        
        # 生成唯一的Agno KB ID
        import uuid
        agno_kb_id = f"agno-kb-{uuid.uuid4()}"
        
        # 使用Agno KB ID更新数据库记录
        kb.agno_kb_id = agno_kb_id
        db.commit()
        
        print(f"已为 {kb.name} 初始化Agno知识库，ID为 {agno_kb_id}")
    except Exception as e:
        print(f"初始化Agno知识库时出错: {e}")
        # 用错误更新记录
        kb.settings = {**kb.settings, "initialization_error": str(e)}
        db.commit()

@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseWithStats)
def get_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取知识库及其详细统计信息。
    """
    # 获取知识库
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="未找到知识库")
    
    # 获取文档统计
    doc_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar()
    
    # 获取文件类型分布
    file_types_query = db.query(
        Document.mime_type, 
        func.count(Document.id)
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).group_by(Document.mime_type).all()
    
    file_types = {mime_type: count for mime_type, count in file_types_query}
    
    # 获取令牌计数
    token_count = db.query(func.sum(DocumentChunk.token_count)).join(
        Document, DocumentChunk.document_id == Document.id
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar() or 0
    
    # 创建增强响应
    kb_with_stats = KnowledgeBaseWithStats(
        **{k: getattr(knowledge_base, k) for k in knowledge_base.__table__.columns.keys()},
        document_count=doc_count,
        total_tokens=token_count,
        file_types=file_types
    )
    
    return kb_with_stats

@router.get("/{knowledge_base_id}/stats", response_model=KnowledgeBaseStats)
def get_knowledge_base_stats(
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    获取详细的知识库统计信息。
    """
    # 检查知识库是否存在
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="未找到知识库")
    
    # 获取文档计数
    doc_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar()
    
    # 获取处理状态计数
    processed_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.status == "indexed"
    ).scalar()
    
    pending_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.status.in_(["pending", "processing"])
    ).scalar()
    
    error_count = db.query(func.count(Document.id)).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.status == "error"
    ).scalar()
    
    # 获取文件类型分布
    file_types_query = db.query(
        Document.mime_type, 
        func.count(Document.id)
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).group_by(Document.mime_type).all()
    
    file_types = {mime_type: count for mime_type, count in file_types_query}
    
    # 获取令牌计数
    token_count = db.query(func.sum(DocumentChunk.token_count)).join(
        Document, DocumentChunk.document_id == Document.id
    ).filter(
        Document.knowledge_base_id == knowledge_base_id
    ).scalar() or 0
    
    return KnowledgeBaseStats(
        document_count=doc_count,
        total_tokens=token_count,
        processed_count=processed_count,
        pending_count=pending_count,
        error_count=error_count,
        file_types=file_types
    )

@router.put("/{knowledge_base_id}", response_model=KnowledgeBaseSchema)
def update_knowledge_base(
    knowledge_base_id: int,
    knowledge_base_update: KnowledgeBaseUpdate,
    db: Session = Depends(get_db)
):
    """
    更新知识库。
    """
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="未找到知识库")
    
    # 更新提供的字段
    update_data = knowledge_base_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(knowledge_base, field, value)
    
    db.commit()
    db.refresh(knowledge_base)
    return knowledge_base

@router.delete("/{knowledge_base_id}")
def delete_knowledge_base(
    knowledge_base_id: int,
    permanent: bool = False,
    db: Session = Depends(get_db)
):
    """
    删除或停用知识库。
    """
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="未找到知识库")
    
    if permanent:
        # 删除文档和块
        documents = db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id).all()
        for doc in documents:
            # 删除块
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
        
        # 删除文档
        db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id).delete()
        
        # 删除知识库
        db.delete(knowledge_base)
        db.commit()
        
        return {"message": "知识库永久删除"}
    else:
        # 软删除，设置is_active为False
        knowledge_base.is_active = False
        db.commit()
        
        return {"message": "知识库停用成功"}

# 文档管理端点
@router.get("/{knowledge_base_id}/documents", response_model=DocumentListResponse)
def get_documents(
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
        raise HTTPException(status_code=404, detail="未找到知识库")
    
    # 构建基本查询
    query = db.query(Document).filter(Document.knowledge_base_id == knowledge_base_id)
    
    # 应用过滤器
    if search:
        query = query.filter(Document.title.ilike(f"%{search}%"))
    
    if status:
        query = query.filter(Document.status == status)
    
    if mime_type:
        query = query.filter(Document.mime_type == mime_type)
    
    # 获取总数
    total_count = query.count()
    
    # 应用排序
    if sort_by:
        sort_column = getattr(Document, sort_by, Document.created_at)
        if sort_order.lower() == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()
        query = query.order_by(sort_column)
    
    # 应用分页
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size)
    
    # 获取结果
    documents = query.all()
    
    return DocumentListResponse(
        items=documents,
        total=total_count,
        page=page,
        page_size=page_size
    )

@router.post("/{knowledge_base_id}/documents", response_model=DocumentSchema)
async def create_document(
    knowledge_base_id: int,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    向知识库添加新文档，可以通过上传文件或直接提供内容。
    使用Agno进行文档处理和索引。
    """
    # 检查知识库是否存在
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="未找到知识库")
    
    if file is None and content is None:
        raise HTTPException(status_code=400, detail="必须提供文件或内容")
    
    # 创建文档记录
    document = Document(
        knowledge_base_id=knowledge_base_id,
        title=title,
        status="pending"
    )
    
    if file:
        # 处理上传文件
        file_content = await file.read()
        mime_type = file.content_type
        file_size = len(file_content)
        
        document.mime_type = mime_type
        document.file_size = file_size
        
        if mime_type.startswith("text/"):
            document.content = file_content.decode()
        
        # 上传文件到对象存储（MinIO）
        file_path = f"knowledge-bases/{knowledge_base_id}/documents/{file.filename}"
        upload_result = upload_file(
            file_data=file.file,
            object_name=file_path,
            content_type=mime_type
        )
        
        document.file_path = file_path
        document.metadata = {
            "filename": file.filename,
            "content_type": mime_type,
            "size": file_size,
            "upload_date": datetime.now().isoformat()
        }
    else:
        # 保存直接内容
        document.content = content
        document.mime_type = "text/plain"
        document.file_size = len(content.encode())
        document.metadata = {
            "source": "direct_input",
            "content_type": "text/plain",
            "size": len(content.encode()),
            "creation_date": datetime.now().isoformat()
        }
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # 在后台使用Agno处理文档
    background_tasks.add_task(
        process_document_with_agno,
        document.id,
        db
    )
    
    return document

async def process_document_with_agno(document_id: int, db: Session):
    """使用Agno的知识库功能处理文档"""
    # 获取文档
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        print(f"未找到文档 {document_id} 用于Agno处理")
        return
    
    # 更新状态
    document.status = "processing"
    db.commit()
    
    try:
        # 获取知识库
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == document.knowledge_base_id).first()
        if not kb:
            raise ValueError(f"未找到知识库 {document.knowledge_base_id}")
        
        # 初始化Agno KB处理器
        kb_processor = KnowledgeBaseProcessor(
            kb_id=str(kb.id),
            name=kb.name
        )
        
        # 准备文档数据
        doc_data = {
            "content": document.content,
            "metadata": {
                **document.metadata,
                "document_id": document.id,
                "title": document.title,
                "mime_type": document.mime_type
            }
        }
        
        # 向Agno知识库添加文档
        result = await kb_processor.add_document(doc_data)
        
        # 存储块信息
        # 在真实实现中，我们将从结果中提取实际块
        # 目前，我们将创建模拟块
        from app.utils.text_processing import count_tokens
        
        if document.content:
            # 计算令牌数
            token_count = count_tokens(document.content)
            
            # 模拟块（在真实实现中，这将来自Agno）
            chunk_size = 1000
            chunks = [document.content[i:i+chunk_size] for i in range(0, len(document.content), chunk_size)]
            
            for i, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk_text,
                    metadata={
                        "chunk_index": i,
                        "document_id": document.id
                    },
                    embedding_id=f"doc-{document.id}-chunk-{i}",
                    token_count=count_tokens(chunk_text)
                )
                db.add(chunk)
            
            # 更新文档和知识库统计
            document.status = "indexed"
            kb.total_documents += 1
            kb.total_tokens += token_count
            
            db.commit()
        else:
            document.status = "error"
            document.error_message = "没有内容可处理"
            db.commit()
    
    except Exception as e:
        # 更新文档状态为错误
        document.status = "error"
        document.error_message = str(e)
        db.commit()
        print(f"使用Agno处理文档时出错: {e}")

@router.get("/{knowledge_base_id}/documents/{document_id}", response_model=DocumentSchema)
def get_document(
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
    document = db.query(Document).filter(
        Document.knowledge_base_id == knowledge_base_id,
        Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="未找到文档")
    
    # 首先删除文档块
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    
    # 从数据库中删除文档
    db.delete(document)
    db.commit()
    
    # 在后台从Agno中删除文档
    background_tasks.add_task(
        remove_document_from_agno,
        knowledge_base_id,
        document_id
    )
    
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

# 帮助函数，用于计算令牌数，因为我们尚未直接导入Agno
def count_tokens(text: str) -> int:
    """计算文本字符串中的令牌数（占位函数）"""
    import re
    # 简单近似：每4个字符一个令牌
    return len(re.findall(r'\S+', text)) + len(text) // 4
