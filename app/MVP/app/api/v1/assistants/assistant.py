"""
AI助手接口
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_async_db
from app.api.dependencies import get_current_user
from app.services.assistants.assistant import AssistantService
from app.services.assistants.conversation import ConversationService
from app.schemas.assistants.assistant import (
    AssistantCreateRequest,
    AssistantUpdateRequest,
    AssistantResponse,
    AssistantListResponse,
    AssistantSearchRequest
)
from app.schemas.assistants.conversation import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationListResponse,
    MessageCreateRequest,
    MessageResponse,
    ConversationWithMessagesResponse
)
from app.schemas.assistants.base import APIResponse
from app.core.assistants.exceptions import (
    AssistantNotFoundError,
    ConversationNotFoundError,
    PermissionDeniedError,
    ValidationError,
    QuotaExceededError
)

router = APIRouter()


# 依赖注入
def get_assistant_service(db: AsyncSession = Depends(get_async_db)) -> AssistantService:
    return AssistantService(db)


def get_conversation_service(db: AsyncSession = Depends(get_async_db)) -> ConversationService:
    return ConversationService(db)


# ========== 助手管理接口 ==========

@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
        request: AssistantCreateRequest,
        current_user=Depends(get_current_user),
        service: AssistantService = Depends(get_assistant_service)
):
    """
    创建AI助手

    - **name**: 助手名称
    - **model**: AI模型 (gpt-3.5-turbo, gpt-4, deepseek-chat, deepseek-coder)
    - **capabilities**: 能力列表 (text, code, math, creative, analysis)
    """
    try:
        assistant = await service.create(request, current_user.id)
        return APIResponse(
            data=assistant,
            message="助手创建成功"
        )
    except QuotaExceededError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="创建助手失败")


@router.get("/", response_model=APIResponse)
async def list_assistants(
        search: Optional[str] = Query(None, description="搜索关键词"),
        category: Optional[str] = Query(None, description="分类"),
        is_public: Optional[bool] = Query(None, description="是否公开"),
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        current_user=Depends(get_current_user),
        service: AssistantService = Depends(get_assistant_service)
):
    """获取助手列表"""
    filters = {
        "search": search,
        "category": category,
        "is_public": is_public
    }
    pagination = {
        "skip": skip,
        "limit": limit
    }

    result = await service.list(
        user_id=current_user.id,
        filters=filters,
        pagination=pagination
    )

    return APIResponse(data=result)


@router.get("/{assistant_id}", response_model=APIResponse)
async def get_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        current_user=Depends(get_current_user),
        service: AssistantService = Depends(get_assistant_service)
):
    """获取助手详情"""
    try:
        assistant = await service.get_by_id(assistant_id, current_user.id)
        return APIResponse(data=assistant)
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="无权访问该助手")


@router.put("/{assistant_id}", response_model=APIResponse)
async def update_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        request: AssistantUpdateRequest = None,
        current_user=Depends(get_current_user),
        service: AssistantService = Depends(get_assistant_service)
):
    """更新助手信息"""
    try:
        assistant = await service.update(assistant_id, request, current_user.id)
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


@router.delete("/{assistant_id}", response_model=APIResponse)
async def delete_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        current_user=Depends(get_current_user),
        service: AssistantService = Depends(get_assistant_service)
):
    """删除助手"""
    try:
        success = await service.delete(assistant_id, current_user.id)
        if success:
            return APIResponse(message="助手删除成功")
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有所有者可以删除助手")


# ========== 知识库管理接口 ==========

@router.post("/{assistant_id}/knowledge-bases/{kb_id}", response_model=APIResponse)
async def add_knowledge_base(
        assistant_id: int = Path(..., description="助手ID"),
        kb_id: int = Path(..., description="知识库ID"),
        current_user=Depends(get_current_user),
        service: AssistantService = Depends(get_assistant_service)
):
    """添加知识库到助手"""
    try:
        success = await service.add_knowledge_base(assistant_id, kb_id, current_user.id)
        if success:
            return APIResponse(message="知识库添加成功")
        else:
            raise HTTPException(status_code=500, detail="添加失败")
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有所有者可以管理知识库")


@router.delete("/{assistant_id}/knowledge-bases/{kb_id}", response_model=APIResponse)
async def remove_knowledge_base(
        assistant_id: int = Path(..., description="助手ID"),
        kb_id: int = Path(..., description="知识库ID"),
        current_user=Depends(get_current_user),
        service: AssistantService = Depends(get_assistant_service)
):
    """从助手移除知识库"""
    try:
        success = await service.remove_knowledge_base(assistant_id, kb_id, current_user.id)
        if success:
            return APIResponse(message="知识库移除成功")
        else:
            raise HTTPException(status_code=500, detail="移除失败")
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="只有所有者可以管理知识库")


# ========== 对话管理接口 ==========

@router.post("/{assistant_id}/conversations", response_model=APIResponse)
async def create_conversation(
        assistant_id: int = Path(..., description="助手ID"),
        title: Optional[str] = None,
        current_user=Depends(get_current_user),
        service: ConversationService = Depends(get_conversation_service)
):
    """创建对话"""
    try:
        conversation = await service.create_conversation(
            assistant_id=assistant_id,
            user_id=current_user.id,
            title=title
        )
        return APIResponse(
            data=conversation,
            message="对话创建成功"
        )
    except AssistantNotFoundError:
        raise HTTPException(status_code=404, detail="助手不存在")
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="无权使用该助手")


@router.get("/conversations", response_model=APIResponse)
async def list_conversations(
        assistant_id: Optional[int] = Query(None, description="助手ID筛选"),
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        current_user=Depends(get_current_user),
        service: ConversationService = Depends(get_conversation_service)
):
    """获取用户的对话列表"""
    conversations = await service.get_user_conversations(
        user_id=current_user.id,
        assistant_id=assistant_id,
        skip=skip,
        limit=limit
    )

    return APIResponse(data={
        "items": conversations,
        "total": len(conversations),
        "skip": skip,
        "limit": limit
    })


@router.post("/conversations/{conversation_id}/messages", response_model=APIResponse)
async def send_message(
        conversation_id: int = Path(..., description="对话ID"),
        request: MessageCreateRequest = None,
        current_user=Depends(get_current_user),
        service: ConversationService = Depends(get_conversation_service)
):
    """发送消息"""
    try:
        message = await service.send_message(
            conversation_id=conversation_id,
            content=request.content,
            user_id=current_user.id
        )
        return APIResponse(data=message)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="对话不存在")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/conversations/{conversation_id}/messages", response_model=APIResponse)
async def get_messages(
        conversation_id: int = Path(..., description="对话ID"),
        limit: int = Query(50, ge=1, le=100),
        current_user=Depends(get_current_user),
        service: ConversationService = Depends(get_conversation_service)
):
    """获取对话消息历史"""
    try:
        messages = await service.get_messages(
            conversation_id=conversation_id,
            user_id=current_user.id,
            limit=limit
        )
        return APIResponse(data=messages)
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="对话不存在")


@router.delete("/conversations/{conversation_id}", response_model=APIResponse)
async def delete_conversation(
        conversation_id: int = Path(..., description="对话ID"),
        current_user=Depends(get_current_user),
        service: ConversationService = Depends(get_conversation_service)
):
    """删除对话"""
    try:
        success = await service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
        if success:
            return APIResponse(message="对话删除成功")
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="对话不存在")