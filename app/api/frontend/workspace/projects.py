"""
Frontend API - 助手工作空间接口
提供助手管理、对话管理等功能（基于原项目实际业务模型）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from app.api.frontend.dependencies import (
    FrontendServiceContainer,
    FrontendContext,
    get_frontend_service_container,
    get_frontend_context
)
from app.api.shared.responses import InternalResponseFormatter
from app.api.shared.validators import ValidatorFactory

logger = logging.getLogger(__name__)

router = APIRouter()


# ================================
# 请求/响应模型
# ================================

class AssistantCreateRequest(BaseModel):
    """助手创建请求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="助手名称")
    description: Optional[str] = Field(None, max_length=500, description="助手描述")
    model: str = Field(..., description="使用的模型")
    capabilities: List[str] = Field(default=[], description="助手能力")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    knowledge_base_ids: List[int] = Field(default=[], description="关联的知识库ID")


class ConversationCreateRequest(BaseModel):
    """对话创建请求模型"""
    assistant_id: int = Field(..., description="助手ID")
    title: Optional[str] = Field(None, max_length=255, description="对话标题")


# ================================
# 助手管理接口实现
# ================================

@router.get("/assistants", response_model=Dict[str, Any], summary="获取用户助手列表")
async def list_assistants(
    capabilities: Optional[List[str]] = Query(None, description="能力筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户可访问的助手列表
    """
    try:
        logger.info(f"Frontend API - 获取助手列表: user_id={context.user.id}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 获取助手列表
        assistants_data = await assistant_service.get_assistants(
            skip=offset,
            limit=limit,
            capabilities=capabilities
        )
        
        # 如果有搜索关键词，进行过滤
        if search:
            assistants_data = [
                assistant for assistant in assistants_data
                if search.lower() in assistant.name.lower() 
                or (assistant.description and search.lower() in assistant.description.lower())
            ]
        
        # 构建响应数据
        response_data = {
            "assistants": [assistant.to_dict() for assistant in assistants_data],
            "total": len(assistants_data),
            "limit": limit,
            "offset": offset
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取助手列表成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取助手列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取助手列表失败"
        )


@router.post("/assistants", response_model=Dict[str, Any], summary="创建助手")
async def create_assistant(
    request: AssistantCreateRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    创建新的AI助手
    """
    try:
        logger.info(f"Frontend API - 创建助手: user_id={context.user.id}, name={request.name}")
        
        # 获取助手服务
        assistant_service = container.get_assistant_service()
        
        # 构建助手创建数据
        assistant_data = {
            "name": request.name,
            "description": request.description,
            "model": request.model,
            "capabilities": request.capabilities,
            "system_prompt": request.system_prompt
        }
        
        # 创建助手
        assistant = await assistant_service.create_assistant(assistant_data)
        
        # 关联知识库（如果指定）
        if request.knowledge_base_ids:
            for kb_id in request.knowledge_base_ids:
                await assistant_service.add_knowledge_base(assistant.id, kb_id)
        
        return InternalResponseFormatter.format_success(
            data=assistant.to_dict(),
            message="助手创建成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 创建助手失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="助手创建失败"
        )


@router.get("/conversations", response_model=Dict[str, Any], summary="获取对话列表")
async def list_conversations(
    assistant_id: Optional[int] = Query(None, description="助手ID筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    获取用户的对话列表
    """
    try:
        logger.info(f"Frontend API - 获取对话列表: user_id={context.user.id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 获取对话列表
        conversations = await chat_service.get_user_conversations(
            user_id=context.user.id,
            assistant_id=assistant_id,
            skip=offset,
            limit=limit
        )
        
        # 构建响应数据
        response_data = {
            "conversations": [conv.to_dict() for conv in conversations],
            "total": len(conversations),
            "limit": limit,
            "offset": offset
        }
        
        return InternalResponseFormatter.format_success(
            data=response_data,
            message="获取对话列表成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 获取对话列表失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="获取对话列表失败"
        )


@router.post("/conversations", response_model=Dict[str, Any], summary="创建对话")
async def create_conversation(
    request: ConversationCreateRequest,
    container: FrontendServiceContainer = Depends(get_frontend_service_container),
    context: FrontendContext = Depends(get_frontend_context)
):
    """
    创建新的对话会话
    """
    try:
        logger.info(f"Frontend API - 创建对话: user_id={context.user.id}, assistant_id={request.assistant_id}")
        
        # 获取聊天服务
        chat_service = container.get_chat_service()
        
        # 创建对话
        conversation = await chat_service.create_conversation(
            assistant_id=request.assistant_id,
            user_id=context.user.id,
            title=request.title
        )
        
        return InternalResponseFormatter.format_success(
            data=conversation.to_dict(),
            message="对话创建成功"
        )
        
    except Exception as e:
        logger.error(f"Frontend API - 创建对话失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="对话创建失败"
        ) 