from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import base64
import io
import time
from datetime import datetime

from app.models.database import get_db
from app.models.chat import Conversation, Message, MessageReference
from app.models.assistants import Assistant
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
from app.core.chat.chat_service import process_chat_request

router = APIRouter()


def get_voice_manager():
    """依赖注入：获取语音管理器实例"""
    return VoiceAgentManager()

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
    向助手发送文本消息并获取响应。
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
    
    # 如果启用了语音输出，则生成语音
    if chat_request.enable_voice_output:
        try:
            voice_manager = VoiceAgentManager()
            voice_params = {
                "enable_voice_output": True,
                "voice": chat_request.voice,
                "speed": chat_request.speed
            }
            
            audio_data = await voice_manager.process_voice_output(response["message"].content, voice_params)
            if audio_data:
                response["audio_data"] = base64.b64encode(audio_data).decode('utf-8')
        except Exception as e:
            print(f"Error generating voice output: {e}")
    
    return response


@router.post("/voice", response_model=ChatResponse)
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
    # 检查助手是否存在
    assistant = db.query(Assistant).filter(Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="未找到助手")
    
    # 处理语音输入
    input_text = message or ""
    transcription_result = None
    
    if audio_file and enable_voice_input:
        try:
            audio_data = await audio_file.read()
            transcription = await voice_manager.process_voice_input(audio_data, {"enable_voice_input": True})
            if transcription:
                input_text = transcription
                transcription_result = {
                    "text": transcription,
                    "success": True,
                    "timestamp": time.time()
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"语音处理错误: {str(e)}")
    
    if not input_text and not audio_file:
        raise HTTPException(status_code=400, detail="必须提供文本消息或语音文件")
    
    # 如果只是要转录，直接返回转录结果
    if transcribe_only and transcription_result:
        return {
            "conversation_id": conversation_id or 0,
            "message": {
                "id": 0,
                "conversation_id": conversation_id or 0,
                "role": "user",
                "content": input_text,
                "created_at": datetime.now()
            },
            "transcription": transcription_result,
            "references": []
        }
    
    # 创建或获取对话
    conversation = None
    if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="未找到对话")
    else:
        # 创建新对话
        title = input_text[:30] + "..." if len(input_text) > 30 else input_text
        conversation = Conversation(
            assistant_id=assistant_id,
            user_id=user_id,
            title=f"对话 {title}"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # 创建用户消息
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=input_text
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # 异步处理聊天请求以生成AI响应
    response = await process_chat_request(
        assistant_id=assistant_id,
        conversation_id=conversation.id,
        user_message=user_message,
        db=db
    )
    
    # 如果启用了语音输出，则生成语音
    if enable_voice_output:
        try:
            voice_params = {
                "enable_voice_output": True,
                "voice": voice,
                "speed": speed
            }
            
            audio_data = await voice_manager.process_voice_output(response["message"].content, voice_params)
            if audio_data:
                response["audio_data"] = base64.b64encode(audio_data).decode('utf-8')
        except Exception as e:
            print(f"Error generating voice output: {e}")
    
    return response


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
