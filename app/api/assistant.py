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

from app.models.database import get_db
from app.models.assistant import Assistant, Conversation, Message
from app.models.knowledge import KnowledgeBase
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
from app.utils.object_storage import upload_file, get_file_url
from app.utils.rate_limiter import RateLimiter
from app.utils.template_renderer import render_assistant_page
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
    # 创建助手记录
    db_assistant = Assistant(
        name=assistant.name,
        description=assistant.description,
        model=assistant.model,
        capabilities=assistant.capabilities,
        configuration=assistant.configuration,
        system_prompt=assistant.system_prompt
    )
    
    # 如果指定了知识库，添加知识库关系
    if assistant.knowledge_base_ids:
        knowledge_bases = db.query(KnowledgeBase).filter(
            KnowledgeBase.id.in_(assistant.knowledge_base_ids)
        ).all()
        
        if len(knowledge_bases) != len(assistant.knowledge_base_ids):
            raise HTTPException(status_code=400, detail="一个或多个知识库未找到")
        
        db_assistant.knowledge_bases = knowledge_bases
    
    # 添加到数据库
    db.add(db_assistant)
    db.commit()
    db.refresh(db_assistant)
    
    # 为助手生成访问URL
    access_url = f"{settings.BASE_URL}/assistants/web/{db_assistant.id}"
    db_assistant.access_url = access_url
    db.commit()
    
    return db_assistant

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
    query = db.query(Assistant)
    
    # 如果指定了能力，按能力过滤
    if capabilities:
        for capability in capabilities:
            query = query.filter(Assistant.capabilities.contains([capability]))
    
    assistants = query.offset(skip).limit(limit).all()
    return {"assistants": assistants, "total": query.count()}

@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取助手详情
    """
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="助手未找到")
    
    return assistant

@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: int,
    assistant_update: AssistantUpdate,
    db: Session = Depends(get_db)
):
    """
    更新助手
    """
    db_assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=404, detail="助手未找到")
    
    # 更新基本字段
    update_data = assistant_update.dict(exclude_unset=True)
    
    # 单独处理知识库关系
    if "knowledge_base_ids" in update_data:
        kb_ids = update_data.pop("knowledge_base_ids")
        if kb_ids:
            knowledge_bases = db.query(KnowledgeBase).filter(
                KnowledgeBase.id.in_(kb_ids)
            ).all()
            
            if len(knowledge_bases) != len(kb_ids):
                raise HTTPException(status_code=400, detail="一个或多个知识库未找到")
            
            db_assistant.knowledge_bases = knowledge_bases
    
    # 更新剩余字段
    for key, value in update_data.items():
        setattr(db_assistant, key, value)
    
    db.commit()
    db.refresh(db_assistant)
    return db_assistant

@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: int,
    db: Session = Depends(get_db)
):
    """
    删除助手
    """
    db_assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not db_assistant:
        raise HTTPException(status_code=404, detail="助手未找到")
    
    db.delete(db_assistant)
    db.commit()
    return {"message": "助手已成功删除"}

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
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="助手未找到")
    
    # 创建对话
    db_conversation = Conversation(
        assistant_id=assistant_id,
        title=conversation.title or f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        metadata=conversation.metadata
    )
    
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    return db_conversation
