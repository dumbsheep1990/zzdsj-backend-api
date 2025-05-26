"""
助手管理API模块: 提供助手资源的CRUD操作和知识库关联管理
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.assistants import Assistant, AssistantKnowledgeBase
from app.schemas.assistants import (
    Assistant as AssistantSchema,
    AssistantCreate,
    AssistantUpdate,
    AssistantWithKnowledgeBases
)
from app.api.frontend.dependencies import ResponseFormatter

router = APIRouter()

@router.get("/", response_model=List[AssistantSchema])
def get_assistants(
    skip: int = 0, 
    limit: int = 100, 
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取所有助手，支持可选过滤。
    """
    query = db.query(Assistant)
    
    if is_active is not None:
        query = query.filter(Assistant.is_active == is_active)
    
    assistants = query.offset(skip).limit(limit).all()
    return ResponseFormatter.format_success(assistants)

@router.post("/", response_model=AssistantSchema, status_code=status.HTTP_201_CREATED)
def create_assistant(
    assistant: AssistantCreate,
    db: Session = Depends(get_db)
):
    """
    创建新助手。
    """
    db_assistant = Assistant(
        name=assistant.name,
        description=assistant.description,
        model_id=assistant.model_id,
        capabilities=assistant.capabilities
    )
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    return ResponseFormatter.format_success(db_assistant)

@router.get("/{assistant_id}", response_model=AssistantWithKnowledgeBases)
def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取助手及其关联的知识库。
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到助手")
    return ResponseFormatter.format_success(assistant)

@router.put("/{assistant_id}", response_model=AssistantSchema)
def update_assistant(
    assistant_id: int,
    assistant_update: AssistantUpdate,
    db: Session = Depends(get_db)
):
    """
    更新助手。
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到助手")
    
    # 更新提供的字段
    update_data = assistant_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assistant, field, value)
    
    db.commit()
    db.refresh(assistant)
    return ResponseFormatter.format_success(assistant)

@router.delete("/{assistant_id}")
def delete_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    删除或停用助手。
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到助手")
    
    # 通过设置is_active为False进行软删除
    assistant.is_active = False
    db.commit()
    
    return ResponseFormatter.format_success(None, message="助手成功停用")

@router.post("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
def link_knowledge_base(
    assistant_id: int,
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    将知识库关联到助手。
    """
    # 检查助手是否存在
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到助手")
    
    # 检查知识库是否存在
    from app.models.knowledge import KnowledgeBase
    knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
    if not knowledge_base:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到知识库")
    
    # 检查关联是否已存在
    existing_link = db.query(AssistantKnowledgeBase).filter(
        AssistantKnowledgeBase.assistant_id == assistant_id,
        AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
    ).first()
    
    if existing_link:
        return ResponseFormatter.format_success(None, message="该知识库已经关联到此助手")
    
    # 创建关联
    link = AssistantKnowledgeBase(
        assistant_id=assistant_id,
        knowledge_base_id=knowledge_base_id
    )
    db.add(link)
    db.commit()
    
    return ResponseFormatter.format_success(None, message="知识库成功关联到助手")

@router.delete("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
def unlink_knowledge_base(
    assistant_id: int,
    knowledge_base_id: int,
    db: Session = Depends(get_db)
):
    """
    解除助手与知识库的关联。
    """
    # 检查关联是否存在
    link = db.query(AssistantKnowledgeBase).filter(
        AssistantKnowledgeBase.assistant_id == assistant_id,
        AssistantKnowledgeBase.knowledge_base_id == knowledge_base_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到关联关系")
    
    # 删除关联
    db.delete(link)
    db.commit()
    
    return ResponseFormatter.format_success(None, message="已解除助手与知识库的关联") 