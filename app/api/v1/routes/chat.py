"""
聊天API路由
提供统一的聊天交互接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import time
from datetime import datetime
import logging

from app.models.database import get_db
from app.models.chat import Conversation, Message
from app.models.assistants import Assistant
from app.schemas.chat import (
    Conversation as ConversationSchema,
    ConversationCreate,
    ConversationUpdate,
    ConversationWithMessages,
    Message as MessageSchema,
    MessageCreate,
    ChatRequest,
    ChatResponse
)
from app.api.v1.dependencies import (
    get_chat_adapter, get_request_context, ResponseFormatter
)
from app.messaging.adapters.chat import ChatAdapter
from app.messaging.core.models import (
    Message as CoreMessage, MessageRole, TextMessage
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/conversations", response_model=List[ConversationSchema])
async def get_conversations(
    assistant_id: Optional[int] = None,
    user_id: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取所有对话，支持可选过滤。
    """
    query = db.query(Conversation)
    
    if assistant_id:
        query = query.filter(Conversation.assistant_id == assistant_id)
    
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    
    conversations = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
    return ResponseFormatter.format_success(conversations)


@router.post("/conversations", response_model=ConversationSchema)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    """
    创建新对话。
    """
    # 检查助手是否存在
    if conversation.assistant_id:
        assistant = db.query(Assistant).filter(Assistant.id == conversation.assistant_id).first()
        if not assistant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="助手不存在")
    
    # 创建对话记录
    db_conversation = Conversation(
        title=conversation.title,
        assistant_id=conversation.assistant_id,
        user_id=conversation.user_id,
        metadata=conversation.metadata or {}
    )
    
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    
    return ResponseFormatter.format_success(db_conversation)


@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取对话及其消息。
    """
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    
    # 获取关联的消息
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at).all()
    
    return ResponseFormatter.format_success({
        "conversation": conversation,
        "messages": messages
    })


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    删除对话。
    """
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    
    # 删除关联的消息
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    
    # 删除对话
    db.delete(conversation)
    db.commit()
    
    return ResponseFormatter.format_success(None, message="对话已删除")


@router.post("/send", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    chat_adapter: ChatAdapter = Depends(get_chat_adapter),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    向助手发送消息并获取响应。
    """
    # 检查助手是否存在
    assistant = db.query(Assistant).filter(Assistant.id == chat_request.assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="助手不存在")
    
    # 检查对话是否存在（如果提供了对话ID）
    conversation = None
    if chat_request.conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == chat_request.conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    else:
        # 创建新对话
        conversation = Conversation(
            title=f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            assistant_id=chat_request.assistant_id,
            user_id=chat_request.user_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # 创建用户消息
    user_message = TextMessage(
        content=chat_request.message,
        role=MessageRole.USER
    )
    
    # 更新数据库中的消息记录
    db_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=chat_request.message,
        metadata={}
    )
    db.add(db_message)
    db.commit()
    
    # 使用统一消息系统处理请求
    try:
        # 选择适当的回复格式
        if chat_request.stream:
            # 异步处理返回SSE流
            return await chat_adapter.to_sse_response(
                messages=[user_message],
                model_name=chat_request.model_name,
                temperature=chat_request.temperature,
                system_prompt=assistant.system_prompt,
                memory_key=f"conversation_{conversation.id}"
            )
        else:
            # 同步处理返回JSON
            response_messages = await chat_adapter.process_messages(
                messages=[user_message],
                model_name=chat_request.model_name,
                temperature=chat_request.temperature,
                system_prompt=assistant.system_prompt,
                memory_key=f"conversation_{conversation.id}"
            )
            
            # 保存助手回复到数据库
            for msg in response_messages:
                if msg.role == MessageRole.ASSISTANT and msg.type != "error":
                    content = msg.content
                    if not isinstance(content, str):
                        content = str(content)
                    
                    assistant_message = Message(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=content,
                        metadata={}
                    )
                    db.add(assistant_message)
            
            db.commit()
            
            # 更新对话的最后更新时间
            conversation.updated_at = datetime.now()
            db.commit()
            
            # 使用OpenAI兼容格式返回结果
            return ResponseFormatter.format_openai_compatible(response_messages)
    except Exception as e:
        logger.error(f"聊天处理错误: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"聊天处理出错: {str(e)}")


@router.post("/stream")
async def chat_stream(
    chat_request: ChatRequest,
    chat_adapter: ChatAdapter = Depends(get_chat_adapter),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    流式对话接口，返回SSE格式的响应流。
    """
    # 确保请求使用流模式
    chat_request.stream = True
    return await chat(chat_request, chat_adapter, background_tasks, db)
