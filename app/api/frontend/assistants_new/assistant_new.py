"""
助手API管理模块: 提供与AI助手交互的端点，
支持各种模式（文本、图像、语音）和不同的接口格式
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
import logging

from app.utils.database import get_db
from app.services_new.assistant_service_new import AssistantService
from app.schemas.assistant import (
    AssistantCreate,
    AssistantUpdate,
    AssistantResponse,
    ConversationCreate,
    ConversationResponse,
    AssistantListResponse,
    ConversationListResponse
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.api.dependencies import get_current_user, ResponseFormatter
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_assistant(
        request: AssistantCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建新助手"""
    try:
        service = AssistantService(db)
        assistant = await service.create_assistant(
            data=request.model_dump(),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description,
                "model": assistant.model,
                "capabilities": assistant.capabilities,
                "is_public": assistant.is_public,
                "created_at": assistant.created_at.isoformat()
            },
            message="助手创建成功"
        )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建助手失败")


@router.get("/", response_model=Dict[str, Any])
async def list_assistants(
        category: Optional[str] = Query(None, description="分类筛选"),
        capabilities: Optional[List[str]] = Query(None, description="能力筛选"),
        is_public: Optional[bool] = Query(None, description="公开性筛选"),
        search: Optional[str] = Query(None, description="搜索关键词"),
        tags: Optional[List[str]] = Query(None, description="标签筛选"),
        skip: int = Query(0, ge=0, description="跳过条数"),
        limit: int = Query(20, ge=1, le=100, description="返回条数"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手列表"""
    try:
        service = AssistantService(db)
        assistants, total = await service.get_assistants(
            skip=skip,
            limit=limit,
            user_id=current_user.id,
            category=category,
            capabilities=capabilities,
            is_public=is_public,
            search=search,
            tags=tags
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description,
                        "model": a.model,
                        "category": a.category,
                        "capabilities": a.capabilities,
                        "tags": a.tags,
                        "is_public": a.is_public,
                        "avatar_url": a.avatar_url,
                        "created_at": a.created_at.isoformat(),
                        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
                        "owner_id": a.owner_id,
                        "is_owner": a.owner_id == current_user.id
                    }
                    for a in assistants
                ],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )

    except Exception as e:
        logger.error(f"获取助手列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取助手列表失败")


@router.get("/{assistant_id}", response_model=Dict[str, Any])
async def get_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        include_knowledge_bases: bool = Query(False, description="包含知识库信息"),
        include_statistics: bool = Query(False, description="包含统计信息"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手详情"""
    try:
        service = AssistantService(db)
        assistant = await service.get_assistant_by_id(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        if not assistant:
            raise HTTPException(status_code=404, detail="助手不存在")

        response_data = {
            "id": assistant.id,
            "name": assistant.name,
            "description": assistant.description,
            "model": assistant.model,
            "system_prompt": assistant.system_prompt,
            "capabilities": assistant.capabilities,
            "is_public": assistant.is_public,
            "category": assistant.category,
            "tags": assistant.tags,
            "avatar_url": assistant.avatar_url,
            "config": assistant.config,
            "created_at": assistant.created_at.isoformat(),
            "updated_at": assistant.updated_at.isoformat() if assistant.updated_at else None,
            "owner_id": assistant.owner_id,
            "is_owner": assistant.owner_id == current_user.id
        }

        # 添加知识库信息
        if include_knowledge_bases:
            knowledge_bases = await service.get_assistant_knowledge_bases(assistant_id)
            response_data["knowledge_bases"] = [
                {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "is_public": kb.is_public
                }
                for kb in knowledge_bases
            ]

        # 添加统计信息
        if include_statistics:
            stats = await service.get_assistant_statistics(assistant_id)
            response_data["statistics"] = stats

        return ResponseFormatter.format_success(data=response_data)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取助手详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取助手详情失败")


@router.put("/{assistant_id}", response_model=Dict[str, Any])
async def update_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        request: AssistantUpdate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新助手信息"""
    try:
        service = AssistantService(db)
        assistant = await service.update_assistant(
            assistant_id=assistant_id,
            data=request.model_dump(exclude_unset=True),
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": assistant.id,
                "name": assistant.name,
                "description": assistant.description,
                "model": assistant.model,
                "updated_at": assistant.updated_at.isoformat()
            },
            message="助手更新成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新助手失败")


@router.delete("/{assistant_id}")
async def delete_assistant(
        assistant_id: int = Path(..., description="助手ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除助手"""
    try:
        service = AssistantService(db)
        success = await service.delete_assistant(
            assistant_id=assistant_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="删除助手失败")

        return ResponseFormatter.format_success(
            data={"assistant_id": assistant_id},
            message="助手删除成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除助手失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除助手失败")


# ==================== 知识库管理接口 ====================

@router.post("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
async def link_knowledge_base(
        assistant_id: int = Path(..., description="助手ID"),
        knowledge_base_id: int = Path(..., description="知识库ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """关联知识库到助手"""
    try:
        service = AssistantService(db)
        success = await service.add_knowledge_base(
            assistant_id=assistant_id,
            knowledge_base_id=knowledge_base_id,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "assistant_id": assistant_id,
                "knowledge_base_id": knowledge_base_id
            },
            message="知识库关联成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"关联知识库失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="关联知识库失败")


@router.delete("/{assistant_id}/knowledge-bases/{knowledge_base_id}")
async def unlink_knowledge_base(
        assistant_id: int = Path(..., description="助手ID"),
        knowledge_base_id: int = Path(..., description="知识库ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """解除助手与知识库的关联"""
    try:
        service = AssistantService(db)
        success = await service.remove_knowledge_base(
            assistant_id=assistant_id,
            knowledge_base_id=knowledge_base_id,
            user_id=current_user.id
        )

        if not success:
            raise HTTPException(status_code=500, detail="解除关联失败")

        return ResponseFormatter.format_success(
            data={
                "assistant_id": assistant_id,
                "knowledge_base_id": knowledge_base_id
            },
            message="已解除知识库关联"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"解除知识库关联失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="解除关联失败")


# ==================== 对话管理接口 ====================

@router.post("/{assistant_id}/conversations", response_model=Dict[str, Any])
async def create_conversation(
        assistant_id: int = Path(..., description="助手ID"),
        request: ConversationCreate = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建对话"""
    try:
        # 确保 assistant_id 一致
        request.assistant_id = assistant_id

        service = AssistantService(db)
        conversation = await service.create_conversation(
            data=request,
            user_id=current_user.id
        )

        return ResponseFormatter.format_success(
            data={
                "id": conversation.id,
                "assistant_id": conversation.assistant_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat()
            },
            message="对话创建成功"
        )

    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建对话失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建对话失败")


@router.get("/conversations", response_model=Dict[str, Any])
async def list_conversations(
        assistant_id: Optional[int] = Query(None, description="助手ID筛选"),
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取用户对话列表"""
    try:
        service = AssistantService(db)
        conversations, total = await service.get_user_conversations(
            user_id=current_user.id,
            assistant_id=assistant_id,
            skip=skip,
            limit=limit
        )

        return ResponseFormatter.format_success(
            data={
                "items": [
                    {
                        "id": c.id,
                        "assistant_id": c.assistant_id,
                        "title": c.title,
                        "created_at": c.created_at.isoformat(),
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None
                    }
                    for c in conversations
                ],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )

    except Exception as e:
        logger.error(f"获取对话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取对话列表失败")


# ==================== 统计接口 ====================

@router.get("/categories/statistics", response_model=Dict[str, Any])
async def get_category_statistics(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取助手分类统计"""
    try:
        service = AssistantService(db)
        categories = await service.get_category_statistics(user_id=current_user.id)

        return ResponseFormatter.format_success(
            data={
                "categories": categories,
                "total_categories": len(categories)
            }
        )

    except Exception as e:
        logger.error(f"获取分类统计失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取分类统计失败")