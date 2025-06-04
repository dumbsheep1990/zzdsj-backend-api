"""
问答助手路由：提供问答助手管理、问题卡片管理和文档关联操作
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import logging

from app.utils.database import get_db
from app.services_new.qa_service import QAService
from app.schemas.assistant_qa import (
    AssistantCreate, AssistantUpdate,
    QuestionCreate, QuestionUpdate,
    AnswerSettingsUpdate, DocumentSegmentSettingsUpdate
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.api.dependencies import get_current_user, ResponseFormatter
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 助手管理接口 ====================

@router.get("/assistants", response_model=Dict[str, Any])
async def list_assistants(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        status: Optional[str] = Query(None, description="状态过滤"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取问答助手列表"""
    try:
        service = QAService(db)
        assistants, total = await service.get_qa_assistants(
            skip=skip,
            limit=limit,
            user_id=current_user.id,
            status=status
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description,
                        "type": a.type,
                        "icon": a.icon,
                        "status": a.status,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None
                    }
                    for a in assistants
                ],
                "total": total
            }
        )

    except Exception as e:
        logger.error(f"获取问答助手列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问答助手列表失败")


@router.get("/assistants/{assistant_id}", response_model=Dict[str, Any])
async def get_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        include_stats: bool = Query(False, description="包含统计信息"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取问答助手详情"""
    try:
        service = QAService(db)
        assistant = await service.get_qa_assistant(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        response_data = {
            "id": assistant.id,
            "name": assistant.name,
            "description": assistant.description,
            "type": assistant.type,
            "icon": assistant.icon,
            "status": assistant.status,
            "created_at": assistant.created_at.isoformat() if assistant.created_at else None,
            "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None,
            "config": assistant.config,
            "knowledge_base_id": assistant.knowledge_base_id
        }

        # 添加统计信息
        if include_stats:
            stats = await service.get_assistant_statistics(assistant_id)
            response_data["stats"] = stats

        return ResponseFormatter.format_success(data=response_data)

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"获取问答助手详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问答助手详情失败")


@router.post("/assistants", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_assistant(
        assistant: AssistantCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建问答助手"""
    try:
        service = QAService(db)
        created = await service.create_qa_assistant(
            data=assistant.model_dump(),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": created.id,
                "name": created.name,
                "description": created.description,
                "type": created.type,
                "icon": created.icon,
                "status": created.status,
                "created_at": created.created_at.isoformat() if created.created_at else None
            },
            message="问答助手创建成功"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建问答助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建问答助手失败")


@router.put("/assistants/{assistant_id}", response_model=Dict[str, Any])
async def update_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        assistant: AssistantUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问答助手信息"""
    try:
        service = QAService(db)
        updated = await service.update_qa_assistant(
            assistant_id=assistant_id,
            data=assistant.model_dump(exclude_unset=True),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "name": updated.name,
                "description": updated.description,
                "updated_at": updated.updated_at.isoformat() if updated.updated_at else None
            },
            message="问答助手更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新问答助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新问答助手失败")


@router.delete("/assistants/{assistant_id}")
async def delete_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除问答助手"""
    try:
        service = QAService(db)
        success = await service.delete_qa_assistant(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="删除助手失败")

        return ResponseFormatter.format_success(
            data={"assistant_id": assistant_id},
            message="问答助手已成功删除"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除问答助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除问答助手失败")


# ==================== 问题管理接口 ====================

@router.get("/assistants/{assistant_id}/questions", response_model=Dict[str, Any])
async def list_questions(
        assistant_id: int = Path(..., description="助手ID"),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手的问题列表"""
    try:
        service = QAService(db)
        questions, total = await service.get_questions(
            assistant_id=assistant_id,
            skip=skip,
            limit=limit,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": q.id,
                        "question": q.question,
                        "answer": q.answer,
                        "category": q.category,
                        "views_count": q.views_count,
                        "created_at": q.created_at.isoformat() if q.created_at else None,
                        "updated_at": q.updated_at.isoformat() if q.updated_at else None
                    }
                    for q in questions
                ],
                "total": total
            }
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"获取问题列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问题列表失败")


@router.get("/questions/{question_id}", response_model=Dict[str, Any])
async def get_question(
        question_id: int = Path(..., description="问题ID"),
        include_document_segments: bool = Query(True, description="包含文档分段"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取问题详情"""
    try:
        service = QAService(db)
        question = await service.get_question(
            question_id=question_id,
            include_document_segments=include_document_segments,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(data={
            "id": question.id,
            "question": question.question,
            "answer": question.answer,
            "category": question.category,
            "views_count": question.views_count,
            "assistant_id": question.assistant_id,
            "created_at": question.created_at.isoformat() if question.created_at else None,
            "updated_at": question.updated_at.isoformat() if question.updated_at else None,
            "document_segments": [
                {
                    "id": seg.id,
                    "content": seg.content,
                    "metadata": seg.metadata
                }
                for seg in getattr(question, 'document_segments', [])
            ] if include_document_segments else None
        })

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"获取问题详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取问题详情失败")


@router.post("/questions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_question(
        question: QuestionCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建问题"""
    try:
        service = QAService(db)
        created = await service.create_question(
            data=question.model_dump(),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": created.id,
                "question": created.question,
                "answer": created.answer,
                "category": created.category,
                "assistant_id": created.assistant_id,
                "created_at": created.created_at.isoformat() if created.created_at else None
            },
            message="问题创建成功"
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建问题失败")


@router.put("/questions/{question_id}", response_model=Dict[str, Any])
async def update_question(
        question_id: int = Path(..., description="问题ID"),
        question: QuestionUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问题信息"""
    try:
        service = QAService(db)
        updated = await service.update_question(
            question_id=question_id,
            data=question.model_dump(exclude_unset=True),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "question": updated.question,
                "answer": updated.answer,
                "updated_at": updated.updated_at.isoformat() if updated.updated_at else None
            },
            message="问题更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新问题失败")


@router.delete("/questions/{question_id}")
async def delete_question(
        question_id: int = Path(..., description="问题ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除问题"""
    try:
        service = QAService(db)
        success = await service.delete_question(
            question_id=question_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="删除问题失败")

        return ResponseFormatter.format_success(
            data={"question_id": question_id},
            message="问题已成功删除"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除问题失败")


# ==================== 问答功能接口 ====================

@router.post("/questions/{question_id}/answer", response_model=Dict[str, Any])
async def answer_question(
        question_id: int = Path(..., description="问题ID"),
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """回答问题"""
    try:
        service = QAService(db)
        answer = await service.answer_question(
            question_id=question_id,
            user_id=current_user.id if current_user else None
        )

        return ResponseFormatter.format_success(
            data={"answer": answer}
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"回答问题失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="回答问题失败")


# ==================== 设置管理接口 ====================

@router.put("/questions/{question_id}/answer-settings", response_model=Dict[str, Any])
async def update_answer_settings(
        question_id: int = Path(..., description="问题ID"),
        settings: AnswerSettingsUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问题回答设置"""
    try:
        service = QAService(db)
        updated = await service.update_answer_settings(
            question_id=question_id,
            answer_mode=settings.answer_mode,
            use_cache=settings.use_cache,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "answer_mode": getattr(updated, 'answer_mode', None),
                "use_cache": getattr(updated, 'use_cache', None)
            },
            message="回答设置更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"更新回答设置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新回答设置失败")


@router.put("/questions/{question_id}/document-settings", response_model=Dict[str, Any])
async def update_document_segment_settings(
        question_id: int = Path(..., description="问题ID"),
        settings: DocumentSegmentSettingsUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新问题文档分段设置"""
    try:
        service = QAService(db)
        updated = await service.update_document_segment_settings(
            question_id=question_id,
            segment_ids=settings.segment_ids,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": updated.id,
                "segment_count": len(settings.segment_ids)
            },
            message="文档分段设置更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"更新文档分段设置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新文档分段设置失败")