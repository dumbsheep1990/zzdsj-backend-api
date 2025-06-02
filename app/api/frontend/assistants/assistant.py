"""
助手API模块: 提供与AI助手交互的端点，
支持各种模式（文本、图像、语音）和不同的接口格式
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
from app.services.assistant_service import AssistantService
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
from app.frameworks.agno import AgnoAgent, create_knowledge_agent
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
    db: Session = Depends(get_db)
):
    """
    创建新助手
    """
    service = AssistantService(db)
    db_assistant = await service.create_assistant(assistant)
    return ResponseFormatter.format_success(db_assistant)

@router.get("/", response_model=AssistantList)
async def list_assistants(
    skip: int = 0,
    limit: int = 100,
    capabilities: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """
    列出所有助手，可选择按能力过滤
    """
    service = AssistantService(db)
    assistants = await service.get_assistants(skip, limit, capabilities)
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
    db: Session = Depends(get_db)
):
    """
    更新助手
    """
    service = AssistantService(db)
    updated_assistant = await service.update_assistant(assistant_id, assistant_update)
    return ResponseFormatter.format_success(updated_assistant)

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