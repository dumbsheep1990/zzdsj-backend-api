"""
问答助手API接口
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.api.dependencies import get_current_user
from app.services.assistants.qa import QAService
from app.schemas.assistants.qa import (
    QAAssistantCreateRequest,
    QAAssistantUpdateRequest,
    QuestionCreateRequest,
    QuestionUpdateRequest,
    AnswerSettingsRequest,
    DocumentSegmentSettingsRequest
)
from app.schemas.assistants.base import APIResponse
from app.core.assistants.exceptions import (
    AssistantNotFoundError,
    PermissionDeniedError,
    ValidationError
)

router = APIRouter()


def get_qa_service(db: Session = Depends(get_db)) -> QAService:
    return QAService(db)


# ========== 助手管理 ==========

@router.post("/assistants", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_qa_assistant(
        request: QAAssistantCreateRequest,
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """创建问答助手"""
    try:
        assistant = await service.create_qa_assistant(request, current_user.id)
        return APIResponse(
            data=assistant,
            message="问答助手创建成功"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assistants", response_model=APIResponse)
async def list_qa_assistants(
        status: Optional[str] = Query(None, description="状态过滤"),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """获取问答助手列表"""
    assistants, total = await service.list_qa_assistants(
        user_id=current_user.id,
        status=status,
        skip=skip,
        limit=limit
    )

    return APIResponse(
        data={
            "items": assistants,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    )


@router.get("/assistants/{assistant_id}", response_model=APIResponse)
async def get_qa_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """获取问答助手详情"""
    try:
        assistant = await service.get_qa_assistant(assistant_id, current_user.id)
        return APIResponse(data=assistant)
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="无权访问该助手")


@router.put("/assistants/{assistant_id}", response_model=APIResponse)
async def update_qa_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        request: QAAssistantUpdateRequest = None,
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """更新问答助手"""
    try:
        assistant = await service.update_qa_assistant(assistant_id, request, current_user.id)
        return APIResponse(
            data=assistant,
            message="助手更新成功"
        )
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有所有者可以更新助手")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/assistants/{assistant_id}", response_model=APIResponse)
async def delete_qa_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """删除问答助手"""
    try:
        success = await service.delete_qa_assistant(assistant_id, current_user.id)
        if success:
            return APIResponse(message="助手删除成功")
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有所有者可以删除助手")


# ========== 问题管理 ==========

@router.post("/questions", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
        request: QuestionCreateRequest,
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """创建问题"""
    try:
        question = await service.create_question(
            assistant_id=request.assistant_id,
            question=request.question,
            answer=request.answer,
            user_id=current_user.id
        )
        return APIResponse(
            data=question,
            message="问题创建成功"
        )
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有助手所有者可以创建问题")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/questions/{question_id}", response_model=APIResponse)
async def get_question(
        question_id: int = Path(..., description="问题ID"),
        include_segments: bool = Query(False, description="包含文档分段"),
        service: QAService = Depends(get_qa_service)
):
    """获取问题详情"""
    try:
        question = await service.get_question(question_id, include_segments)
        return APIResponse(data=question)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/questions/{question_id}", response_model=APIResponse)
async def update_question(
        question_id: int = Path(..., description="问题ID"),
        request: QuestionUpdateRequest = None,
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """更新问题"""
    try:
        question = await service.update_question(question_id, request, current_user.id)
        return APIResponse(
            data=question,
            message="问题更新成功"
        )
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有助手所有者可以更新问题")


@router.delete("/questions/{question_id}", response_model=APIResponse)
async def delete_question(
        question_id: int = Path(..., description="问题ID"),
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """删除问题"""
    try:
        success = await service.delete_question(question_id, current_user.id)
        if success:
            return APIResponse(message="问题删除成功")
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有助手所有者可以删除问题")


# ========== 问答功能 ==========

@router.post("/questions/{question_id}/answer", response_model=APIResponse)
async def answer_question(
        question_id: int = Path(..., description="问题ID"),
        service: QAService = Depends(get_qa_service)
):
    """回答问题（增加浏览次数）"""
    try:
        answer = await service.answer_question(question_id)
        return APIResponse(data={"answer": answer})
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/assistants/{assistant_id}/questions/search", response_model=APIResponse)
async def search_questions(
        assistant_id: int = Path(..., description="助手ID"),
        q: str = Query(..., description="搜索关键词"),
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        service: QAService = Depends(get_qa_service)
):
    """搜索问题"""
    questions = await service.search_questions(
        assistant_id=assistant_id,
        query=q,
        skip=skip,
        limit=limit
    )

    return APIResponse(data={
        "items": questions,
        "total": len(questions)
    })


@router.get("/assistants/{assistant_id}/questions/popular", response_model=APIResponse)
async def get_popular_questions(
        assistant_id: int = Path(..., description="助手ID"),
        limit: int = Query(10, ge=1, le=50),
        service: QAService = Depends(get_qa_service)
):
    """获取热门问题"""
    questions = await service.get_popular_questions(assistant_id, limit)

    return APIResponse(data=questions)


@router.get("/assistants/{assistant_id}/statistics", response_model=APIResponse)
async def get_statistics(
        assistant_id: int = Path(..., description="助手ID"),
        current_user=Depends(get_current_user),
        service: QAService = Depends(get_qa_service)
):
    """获取助手统计信息"""
    try:
        stats = await service.get_statistics(assistant_id)
        return APIResponse(data=stats)
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")