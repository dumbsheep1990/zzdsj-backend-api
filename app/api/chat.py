from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import base64
import io
import time
from datetime import datetime

from app.utils.database import get_db
from app.services.chat_service import ChatService
from app.core.voice.voice_manager import VoiceAgentManager
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

router = APIRouter()


def get_voice_manager():
    """依赖注入：获取语音管理器实例"""
    return VoiceAgentManager()

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
    service = ChatService(db)
    conversations = await service.get_conversations(
        assistant_id=assistant_id,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    return conversations

@router.post("/conversations", response_model=ConversationSchema)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db)
):
    """
    创建新对话。
    """
    service = ChatService(db)
    db_conversation = await service.create_conversation(conversation)
    return db_conversation

@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    通过ID获取对话及其消息。
    """
    service = ChatService(db)
    conversation = await service.get_conversation_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="未找到对话")
    return conversation

@router.put("/conversations/{conversation_id}", response_model=ConversationSchema)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db)
):
    """
    更新对话。
    """
    service = ChatService(db)
    updated_conversation = await service.update_conversation(conversation_id, conversation_update)
    if not updated_conversation:
        raise HTTPException(status_code=404, detail="未找到对话")
    return updated_conversation

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    删除对话。
    """
    service = ChatService(db)
    success = await service.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="未找到对话")
    return {"message": "对话删除成功"}

@router.post("/chat", response_model=ChatResponse)
async def chat(
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    向助手发送文本消息并获取响应。
    """
    service = ChatService(db)
    response = await service.process_chat(chat_request, background_tasks)
    return response

@router.post("/chat/voice")
async def chat_with_voice(
    assistant_id: int = Form(...),
    conversation_id: Optional[int] = Form(None),
    user_id: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    enable_voice_input: bool = Form(True),
    enable_voice_output: bool = Form(True),
    voice: Optional[str] = Form(None),
    speed: Optional[float] = Form(None),
    transcribe_only: bool = Form(False, description="如果为true，只进行语音转录不进行对话"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    voice_manager: VoiceAgentManager = Depends(get_voice_manager)
):
    """
    通过语音与助手交互，支持语音输入和语音输出。
    
    - **assistant_id**: 助手ID
    - **conversation_id**: 可选的会话ID，如果不提供则创建新会话
    - **user_id**: 可选的用户ID
    - **message**: 可选的文本消息，如果提供语音文件则可不提供
    - **audio_file**: 可选的语音文件，与文本消息至少需提供一项
    - **enable_voice_input**: 是否启用语音输入处理
    - **enable_voice_output**: 是否启用语音输出
    - **voice**: 可选的语音声音
    - **speed**: 可选的语音速度
    """
    service = ChatService(db)
    result = await service.process_voice_chat(
        assistant_id=assistant_id,
        conversation_id=conversation_id,
        user_id=user_id,
        message=message,
        audio_file=audio_file,
        enable_voice_input=enable_voice_input,
        enable_voice_output=enable_voice_output,
        voice=voice,
        speed=speed,
        transcribe_only=transcribe_only,
        background_tasks=background_tasks,
        voice_manager=voice_manager
    )
    
    return result


@router.post("/voice/audio", response_class=StreamingResponse)
async def get_voice_audio(
    text: str = Form(...),
    voice: Optional[str] = Form(None),
    speed: Optional[float] = Form(None),
    voice_manager: VoiceAgentManager = Depends(get_voice_manager)
):
    """
    将文本转换为语音并返回音频流
    
    - **text**: 要转换为语音的文本
    - **voice**: 可选的语音声音
    - **speed**: 可选的语音速度
    """
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")
    
    params = {
        "enable_voice_output": True,
        "voice": voice,
        "speed": speed,
    }
    
    audio_data = await voice_manager.process_voice_output(text, params)
    
    if not audio_data:
        raise HTTPException(status_code=500, detail="语音合成失败")
    
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type="audio/mp3",
        headers={"Content-Disposition": "attachment; filename=speech.mp3"}
    )
