"""
对话管理路由
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query, Path
from app.api.frontend.dependencies import ServiceContainer, get_service_container
from app.schemas.chat import ConversationCreate, ConversationUpdate
from app.api.shared.responses import ResponseFormatter

router = APIRouter()


@router.get("/conversations")
async def list_conversations(
        assistant_id: Optional[int] = Query(None),
        search: Optional[str] = Query(None),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """获取对话列表"""
    service = container.get_conversation_service()

    # 从认证中获取user_id（这里假设已经有认证中间件）
    user_id = 1  # TODO: 从认证上下文获取

    conversations = await service.list_conversations(
        user_id=user_id,
        assistant_id=assistant_id,
        search=search,
        skip=offset,
        limit=limit
    )

    return ResponseFormatter.success(
        data={
            "conversations": conversations,
            "total": len(conversations),
            "limit": limit,
            "offset": offset
        }
    )


@router.post("/conversations")
async def create_conversation(
        data: ConversationCreate,
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """创建对话"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    conversation = await service.create(data, user_id)

    return ResponseFormatter.success(
        data=conversation,
        message="对话创建成功"
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
        conversation_id: int = Path(...),
        include_messages: bool = Query(True),
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """获取对话详情"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    if include_messages:
        conversation = await service.get_with_messages(conversation_id, user_id)
    else:
        conversation = await service.get(conversation_id, user_id)

    if not conversation:
        raise NotFoundError("对话不存在")

    return ResponseFormatter.success(data=conversation)


@router.put("/conversations/{conversation_id}")
async def update_conversation(
        conversation_id: int = Path(...),
        data: ConversationUpdate,
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """更新对话"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    conversation = await service.update(conversation_id, data, user_id)

    if not conversation:
        raise NotFoundError("对话不存在")

    return ResponseFormatter.success(
        data=conversation,
        message="对话更新成功"
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
        conversation_id: int = Path(...),
        container: ServiceContainer = Depends(get_service_container)
) -> Dict[str, Any]:
    """删除对话"""
    service = container.get_conversation_service()
    user_id = 1  # TODO: 从认证上下文获取

    success = await service.delete(conversation_id, user_id)

    if not success:
        raise NotFoundError("对话不存在")

    return ResponseFormatter.success(
        data={"conversation_id": conversation_id},
        message="对话删除成功"
    )