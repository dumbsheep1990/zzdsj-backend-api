"""
助手API模块: 提供与AI助手交互的端点，
支持各种模式（文本、图像、语音）和不同的接口格式
现已集成Agno动态框架支持
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.orm import Session
import asyncio
import json
import os
import uuid
import logging
from datetime import datetime

from app.utils.core.database import get_db
from app.models.assistant import Assistant, Conversation, Message
from app.services.assistants.assistant_service import AssistantService
from app.schemas.assistant import (
    AssistantCreate,
    AssistantUpdate,
    AssistantResponse,
    AssistantList,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    AssistantCapability,
)
from app.schemas.chat import ChatRequest, ChatResponse, MultimodalChatRequest, VoiceChatRequest
# 使用新的Agno动态框架
from app.frameworks.agno.dynamic_agent_factory import get_agent_factory, create_dynamic_agent
from app.frameworks.agno.config import get_user_agno_config, get_system_agno_config, DynamicAgnoConfigManager
from app.utils.storage.object_storage import upload_file, get_file_url
from app.utils.security.rate_limiting import RateLimiter
from app.utils.text.template_renderer import render_assistant_page
from app.api.frontend.dependencies import ResponseFormatter
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# API端点的速率限制器
rate_limiter = RateLimiter(
    requests_per_minute=settings.API_RATE_LIMIT,
    burst_limit=settings.API_BURST_LIMIT
)

@router.post("/", response_model=AssistantResponse)
async def create_assistant(
    assistant: AssistantCreate,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    """
    创建新助手 - 支持Agno动态配置
    """
    try:
        service = AssistantService(db)
        
        # 如果配置中包含Agno特定配置，进行验证
        if assistant.configuration and assistant.configuration.get('framework') == 'agno':
            agno_config = assistant.configuration.get('agno_config', {})
            
            # 验证Agno配置格式
            agent_factory = get_agent_factory()
            test_agent = await agent_factory.create_agent_from_config(
                agno_config, user_id
            )
            
            if not test_agent:
                raise HTTPException(
                    status_code=400, 
                    detail="Agno配置无效，无法创建代理"
                )
        
        db_assistant = await service.create_assistant(assistant)
        return ResponseFormatter.format_success(db_assistant)
        
    except Exception as e:
        logger.error(f"创建助手失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=AssistantList)
async def list_assistants(
    skip: int = 0,
    limit: int = 100,
    capabilities: Optional[List[str]] = Query(None),
    framework: Optional[str] = Query(None, description="过滤框架类型"),
    db: Session = Depends(get_db)
):
    """
    列出所有助手，可选择按能力和框架过滤
    """
    service = AssistantService(db)
    assistants = await service.get_assistants(skip, limit, capabilities, framework)
    return ResponseFormatter.format_success({
        "assistants": assistants, 
        "total": len(assistants)
    })

@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取助手详情
    """
    service = AssistantService(db)
    assistant = await service.get_assistant_by_id(assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="助手未找到")
    
    return ResponseFormatter.format_success(assistant)

@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: int,
    assistant_update: AssistantUpdate,
    user_id: str = Query(..., description="用户ID"),
    db: Session = Depends(get_db)
):
    """
    更新助手 - 支持Agno配置更新
    """
    try:
        service = AssistantService(db)
        
        # 如果更新包含Agno配置，进行验证
        if (assistant_update.configuration and 
            assistant_update.configuration.get('framework') == 'agno'):
            
            agno_config = assistant_update.configuration.get('agno_config', {})
            
            # 验证新的Agno配置
            agent_factory = get_agent_factory()
            test_agent = await agent_factory.create_agent_from_config(
                agno_config, user_id
            )
            
            if not test_agent:
                raise HTTPException(
                    status_code=400, 
                    detail="更新的Agno配置无效"
                )
        
        updated_assistant = await service.update_assistant(assistant_id, assistant_update)
        return ResponseFormatter.format_success(updated_assistant)
        
    except Exception as e:
        logger.error(f"更新助手失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    删除助手
    """
    service = AssistantService(db)
    success = await service.delete_assistant(assistant_id)
    return ResponseFormatter.format_success(None, message="助手删除成功")

# ============ Agno配置管理端点 ============

@router.get("/agno/config/system")
async def get_system_agno_config():
    """获取系统级Agno配置"""
    try:
        config = await get_system_agno_config()
        return ResponseFormatter.format_success(config.to_dict())
    except Exception as e:
        logger.error(f"获取系统Agno配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agno/config/user/{user_id}")
async def get_user_agno_config(
    user_id: str,
    db: Session = Depends(get_db)
):
    """获取用户级Agno配置"""
    try:
        config = await get_user_agno_config(user_id)
        return ResponseFormatter.format_success(config.to_dict())
    except Exception as e:
        logger.error(f"获取用户Agno配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/agno/config/user/{user_id}")
async def update_user_agno_config(
    user_id: str,
    config_updates: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """更新用户级Agno配置"""
    try:
        config_manager = DynamicAgnoConfigManager(db)
        success = await config_manager.update_user_config(user_id, config_updates)
        
        if success:
            return ResponseFormatter.format_success(None, message="用户Agno配置更新成功")
        else:
            raise HTTPException(status_code=400, detail="配置更新失败")
            
    except Exception as e:
        logger.error(f"更新用户Agno配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agno/config/user/{user_id}/reset")
async def reset_user_agno_config(
    user_id: str,
    db: Session = Depends(get_db)
):
    """重置用户Agno配置到系统默认值"""
    try:
        config_manager = DynamicAgnoConfigManager(db)
        success = await config_manager.reset_user_config(user_id)
        
        if success:
            return ResponseFormatter.format_success(None, message="用户Agno配置重置成功")
        else:
            raise HTTPException(status_code=400, detail="配置重置失败")
            
    except Exception as e:
        logger.error(f"重置用户Agno配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Agno代理管理端点 ============

@router.post("/agno/agents/create")
async def create_agno_agent(
    agent_config: Dict[str, Any],
    user_id: str = Query(..., description="用户ID"),
    session_id: Optional[str] = Query(None, description="会话ID"),
    db: Session = Depends(get_db)
):
    """动态创建Agno代理"""
    try:
        agent = await create_dynamic_agent(agent_config, user_id, session_id)
        
        if not agent:
            raise HTTPException(
                status_code=400, 
                detail="无法创建Agno代理，请检查配置"
            )
        
        return ResponseFormatter.format_success({
            "agent_id": str(uuid.uuid4()),  # 临时ID，实际应该由Agent管理
            "name": agent_config.get('name', 'Unnamed Agent'),
            "status": "created",
            "message": "Agno代理创建成功"
        })
        
    except Exception as e:
        logger.error(f"创建Agno代理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agno/agents/{agent_id}/chat")
async def chat_with_agno_agent(
    agent_id: str,
    message: str,
    user_id: str = Query(..., description="用户ID"),
    session_id: Optional[str] = Query(None, description="会话ID"),
    db: Session = Depends(get_db)
):
    """与Agno代理对话"""
    try:
        # 这里需要实现代理会话管理
        # 暂时返回模拟响应
        return ResponseFormatter.format_success({
            "agent_id": agent_id,
            "response": "Agno代理响应功能正在开发中",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Agno代理对话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{assistant_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    assistant_id: int,
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    """
    与助手创建新对话
    """
    # 检查助手是否存在
    service = AssistantService(db)
    assistant = await service.get_assistant_by_id(assistant_id)
    if not assistant:
        raise HTTPException(status_code=404, detail="助手未找到")
    
    # 确保对话有标题
    if not conversation.title:
        conversation.title = f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
    # 确保助手ID正确
    conversation.assistant_id = assistant_id
    
    # 创建对话
    db_conversation = await service.create_conversation(conversation)
    return ResponseFormatter.format_success(db_conversation)

# 其他助手相关API端点也应迁移到这里
# 包括消息管理、多模态交互等 