from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.chat import Conversation, Message, MessageReference
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
from app.core.chat.chat_service import process_chat_request

router = APIRouter()

@router.get("/conversations", response_model=List[ConversationSchema])
def get_conversations(
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
    
    return query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()

@router.post("/conversations", response_model=ConversationSchema)
def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    """
    创建新对话。
    """
    # 检查助手是否存在
    assistant = db.query(Assistant).filter(Assistant.id == conversation.assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="未找到助手")
    
    db_conversation = Conversation(
        assistant_id=conversation.assistant_id,
        user_id=conversation.user_id,
        title=conversation.title,
        metadata=conversation.metadata
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation

@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取对话及其消息。
    """
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="未找到对话")
    return conversation

@router.put("/conversations/{conversation_id}", response_model=ConversationSchema)
def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db)
):
    """
    更新对话。
    """
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="未找到对话")
    
    # 更新提供的字段
    update_data = conversation_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)
    
    db.commit()
    db.refresh(conversation)
    return conversation

@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    删除对话。
    """
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="未找到对话")
    
    # 首先删除所有消息
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    
    # 删除对话
    db.delete(conversation)
    db.commit()
    
    return {"message": "对话删除成功"}

@router.post("/", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    向助手发送消息并获取响应。
    """
    # 检查助手是否存在
    assistant = db.query(Assistant).filter(Assistant.id == chat_request.assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="未找到助手")
    
    # 创建或获取对话
    conversation = None
    if chat_request.conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == chat_request.conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="未找到对话")
    else:
        # 创建新对话
        conversation = Conversation(
            assistant_id=chat_request.assistant_id,
            user_id=chat_request.user_id,
            title=f"对话 {chat_request.message[:30]}..." if len(chat_request.message) > 30 else chat_request.message
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # 创建用户消息
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=chat_request.message
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # 异步处理聊天请求以生成AI响应
    response = await process_chat_request(
        assistant_id=chat_request.assistant_id,
        conversation_id=conversation.id,
        user_message=user_message,
        db=db
    )
    
    return response
