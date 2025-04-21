"""
问答助手API: 提供问答助手管理、问题卡片管理和文档关联操作
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.schemas.assistant_qa import (
    AssistantCreate, AssistantUpdate, AssistantResponse, AssistantList,
    QuestionCreate, QuestionUpdate, QuestionResponse, QuestionList,
    AnswerSettingsUpdate, DocumentSegmentSettingsUpdate
)
from app.core.assistant_qa_manager import AssistantQAManager
from app.utils.database import get_db

router = APIRouter()


# 助手管理接口
@router.get("/assistants", response_model=AssistantList)
async def list_assistants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取问答助手列表"""
    manager = AssistantQAManager(db)
    assistants, total = await manager.get_assistants(skip, limit)
    return {"items": assistants, "total": total}


@router.get("/assistants/{assistant_id}", response_model=AssistantResponse)
def get_assistant(assistant_id: int, db: Session = Depends(get_db)):
    """获取问答助手详情"""
    manager = AssistantQAManager(db)
    assistant = manager.get_assistant(assistant_id)
    
    # 计算问题统计
    total_questions = len(assistant.questions)
    total_views = sum(q.views_count for q in assistant.questions)
    
    # 转换为响应格式
    result = {
        "id": assistant.id,
        "name": assistant.name,
        "description": assistant.description,
        "type": assistant.type,
        "icon": assistant.icon,
        "status": assistant.status,
        "created_at": assistant.created_at,
        "updated_at": assistant.updated_at,
        "config": assistant.config,
        "knowledge_base_id": assistant.knowledge_base_id,
        "stats": {
            "total_questions": total_questions,
            "total_views": total_views
        }
    }
    
    return result


@router.post("/assistants", response_model=AssistantResponse)
async def create_assistant(assistant: AssistantCreate, db: Session = Depends(get_db)):
    """创建问答助手"""
    manager = AssistantQAManager(db)
    created = manager.create_assistant(assistant.model_dump())
    
    # 转换为响应格式
    result = {
        "id": created.id,
        "name": created.name,
        "description": created.description,
        "type": created.type,
        "icon": created.icon,
        "status": created.status,
        "created_at": created.created_at,
        "updated_at": created.updated_at,
        "config": created.config,
        "knowledge_base_id": created.knowledge_base_id,
        "stats": {
            "total_questions": 0,
            "total_views": 0
        }
    }
    
    return result


@router.put("/assistants/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: int, 
    assistant: AssistantUpdate, 
    db: Session = Depends(get_db)
):
    """更新问答助手信息"""
    manager = AssistantQAManager(db)
    updated = manager.update_assistant(assistant_id, assistant.model_dump(exclude_unset=True))
    
    # 计算问题统计
    total_questions = len(updated.questions)
    total_views = sum(q.views_count for q in updated.questions)
    
    # 转换为响应格式
    result = {
        "id": updated.id,
        "name": updated.name,
        "description": updated.description,
        "type": updated.type,
        "icon": updated.icon,
        "status": updated.status,
        "created_at": updated.created_at,
        "updated_at": updated.updated_at,
        "config": updated.config,
        "knowledge_base_id": updated.knowledge_base_id,
        "stats": {
            "total_questions": total_questions,
            "total_views": total_views
        }
    }
    
    return result


@router.delete("/assistants/{assistant_id}")
async def delete_assistant(assistant_id: int, db: Session = Depends(get_db)):
    """删除问答助手"""
    manager = AssistantQAManager(db)
    success = manager.delete_assistant(assistant_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="删除助手失败")
    
    return {"message": "助手已成功删除"}


# 问题管理接口
@router.get("/assistants/{assistant_id}/questions", response_model=QuestionList)
async def list_questions(
    assistant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取助手的问题列表"""
    manager = AssistantQAManager(db)
    questions, total = await manager.get_questions(assistant_id, skip, limit)
    return {"items": questions, "total": total}


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: int,
    include_document_segments: bool = Query(True),
    db: Session = Depends(get_db)
):
    """获取问题详情"""
    manager = AssistantQAManager(db)
    question = manager.get_question(question_id, include_document_segments)
    return question


@router.post("/questions", response_model=QuestionResponse)
async def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    """创建问题"""
    manager = AssistantQAManager(db)
    created = await manager.create_question(question.model_dump())
    return created


@router.put("/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int, 
    question: QuestionUpdate, 
    db: Session = Depends(get_db)
):
    """更新问题信息"""
    manager = AssistantQAManager(db)
    updated = await manager.update_question(question_id, question.model_dump(exclude_unset=True))
    return updated


@router.delete("/questions/{question_id}")
async def delete_question(question_id: int, db: Session = Depends(get_db)):
    """删除问题"""
    manager = AssistantQAManager(db)
    success = manager.delete_question(question_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="删除问题失败")
    
    return {"message": "问题已成功删除"}


@router.post("/questions/{question_id}/answer")
async def answer_question(question_id: int, db: Session = Depends(get_db)):
    """回答问题"""
    manager = AssistantQAManager(db)
    answer = await manager.answer_question(question_id)
    return {"answer": answer}


# 问题设置接口
@router.put("/questions/{question_id}/answer-settings", response_model=QuestionResponse)
async def update_answer_settings(
    question_id: int,
    settings: AnswerSettingsUpdate,
    db: Session = Depends(get_db)
):
    """更新问题回答设置"""
    manager = AssistantQAManager(db)
    updated = await manager.update_answer_settings(
        question_id=question_id,
        answer_mode=settings.answer_mode,
        use_cache=settings.use_cache
    )
    return updated


@router.put("/questions/{question_id}/document-settings", response_model=QuestionResponse)
async def update_document_segment_settings(
    question_id: int,
    settings: DocumentSegmentSettingsUpdate,
    db: Session = Depends(get_db)
):
    """更新问题文档分段设置"""
    manager = AssistantQAManager(db)
    updated = await manager.update_document_segment_settings(
        question_id=question_id,
        segment_ids=settings.segment_ids
    )
    return updated
