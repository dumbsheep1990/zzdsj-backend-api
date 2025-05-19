from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.utils.service_decorators import register_service

from app.models.chat import Conversation, Message, MessageReference
from app.models.assistants import Assistant
from app.core.voice.voice_manager import VoiceAgentManager
from app.schemas.chat import (
    ConversationCreate, 
    ConversationUpdate, 
    Conversation as ConversationSchema,
    MessageCreate,
    ChatRequest,
    ChatResponse
)
from app.core.chat.chat_service import process_chat_request

@register_service(service_type="chat", priority="high", description="聊天交互服务")
class ChatService:
    """
    聊天服务层，管理对话和消息的业务逻辑。
    处理所有与对话和消息相关的数据访问和业务处理。
    """
    
    def __init__(self, db: Session):
        self.db = db
        
    async def get_conversations(self, assistant_id: Optional[int] = None, 
                               user_id: Optional[str] = None, 
                               skip: int = 0, 
                               limit: int = 100) -> List[Conversation]:
        """
        获取会话列表，支持按助手ID和用户ID过滤
        """
        query = self.db.query(Conversation)
        
        if assistant_id:
            query = query.filter(Conversation.assistant_id == assistant_id)
        
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        
        conversations = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
        return conversations
    
    async def create_conversation(self, conversation_data: ConversationCreate) -> Conversation:
        """
        创建新会话
        """
        # 检查助手是否存在
        assistant = self.db.query(Assistant).filter(Assistant.id == conversation_data.assistant_id).first()
        if not assistant:
            raise HTTPException(status_code=404, detail="未找到助手")
        
        db_conversation = Conversation(
            assistant_id=conversation_data.assistant_id,
            user_id=conversation_data.user_id,
            title=conversation_data.title,
            metadata=conversation_data.metadata
        )
        self.db.add(db_conversation)
        self.db.commit()
        self.db.refresh(db_conversation)
        return db_conversation
    
    async def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """
        通过ID获取会话及消息
        """
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        return conversation
    
    async def update_conversation(self, conversation_id: int, conversation_data: ConversationUpdate) -> Optional[Conversation]:
        """
        更新会话信息
        """
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return None
        
        # 更新提供的字段
        update_data = conversation_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(conversation, key, value)
        
        # 更新时间戳
        conversation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    async def delete_conversation(self, conversation_id: int) -> bool:
        """
        删除会话及关联的消息
        """
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            return False
        
        # 首先删除所有关联的消息引用
        self.db.query(MessageReference).filter(
            MessageReference.message_id.in_(
                self.db.query(Message.id).filter(Message.conversation_id == conversation_id)
            )
        ).delete(synchronize_session=False)
        
        # 删除所有关联的消息
        self.db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        
        # 删除会话
        self.db.delete(conversation)
        self.db.commit()
        
        return True
    
    async def create_message(self, message_data: MessageCreate) -> Message:
        """
        创建新消息
        """
        # 检查会话是否存在
        conversation = self.db.query(Conversation).filter(Conversation.id == message_data.conversation_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="未找到会话")
        
        db_message = Message(
            conversation_id=message_data.conversation_id,
            role=message_data.role,
            content=message_data.content,
            metadata=message_data.metadata
        )
        self.db.add(db_message)
        
        # 更新会话的最后更新时间
        conversation.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_message)
        return db_message
    
    async def process_chat(self, chat_request: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
        """
        处理聊天请求并获取响应
        """
        # 检查会话是否存在
        if chat_request.conversation_id:
            conversation = self.db.query(Conversation).filter(Conversation.id == chat_request.conversation_id).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="未找到会话")
        
        # 检查助手是否存在
        assistant = self.db.query(Assistant).filter(Assistant.id == chat_request.assistant_id).first()
        if not assistant:
            raise HTTPException(status_code=404, detail="未找到助手")
        
        # 创建或使用现有会话
        if not chat_request.conversation_id:
            conversation = Conversation(
                assistant_id=chat_request.assistant_id,
                user_id=chat_request.user_id,
                title=chat_request.message[:30] + "..." if len(chat_request.message) > 30 else chat_request.message
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            chat_request.conversation_id = conversation.id
        
        # 创建用户消息
        user_message = Message(
            conversation_id=chat_request.conversation_id,
            role="user",
            content=chat_request.message,
            metadata=chat_request.metadata
        )
        self.db.add(user_message)
        self.db.commit()
        self.db.refresh(user_message)
        
        # 处理聊天请求
        response = await process_chat_request(
            db=self.db,
            assistant=assistant,
            conversation_id=chat_request.conversation_id,
            message=chat_request.message,
            message_id=user_message.id,
            user_id=chat_request.user_id,
            metadata=chat_request.metadata,
            background_tasks=background_tasks
        )
        
        return response
    
    async def process_voice_chat(self, 
                               assistant_id: int,
                               conversation_id: Optional[int],
                               user_id: Optional[str],
                               message: Optional[str],
                               audio_file: Optional[UploadFile],
                               enable_voice_input: bool,
                               enable_voice_output: bool,
                               voice: Optional[str],
                               speed: Optional[float],
                               transcribe_only: bool,
                               background_tasks: BackgroundTasks,
                               voice_manager: VoiceAgentManager) -> Dict[str, Any]:
        """
        处理语音聊天，包括语音转文本和文本转语音
        """
        # 检查助手是否存在
        assistant = self.db.query(Assistant).filter(Assistant.id == assistant_id).first()
        if not assistant:
            raise HTTPException(status_code=404, detail="未找到助手")
        
        # 如果提供了会话ID，验证它是否存在
        if conversation_id:
            conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="未找到会话")
        
        # 处理音频文件的转录
        transcription = None
        if audio_file and enable_voice_input:
            audio_bytes = await audio_file.read()
            transcription = await voice_manager.transcribe_audio(audio_bytes)
            print(f"转录结果: {transcription}")
            
            # 如果只需要转录，返回转录结果
            if transcribe_only:
                return {"transcription": transcription, "message": None, "audio": None}
        
        # 使用转录结果或提供的文本消息
        final_message = transcription if transcription else message
        if not final_message:
            raise HTTPException(status_code=400, detail="需要提供文本消息或音频文件")
        
        # 创建或获取会话
        if not conversation_id:
            # 创建新会话
            conversation = Conversation(
                assistant_id=assistant_id,
                user_id=user_id,
                title=final_message[:30] + "..." if len(final_message) > 30 else final_message
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            conversation_id = conversation.id
        
        # 创建用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=final_message
        )
        self.db.add(user_message)
        self.db.commit()
        
        # 处理聊天请求
        chat_request = ChatRequest(
            assistant_id=assistant_id,
            conversation_id=conversation_id,
            message=final_message,
            user_id=user_id,
            metadata={"source": "voice_chat"}
        )
        
        response = await self.process_chat(chat_request, background_tasks)
        
        # 文本转语音处理
        audio_base64 = None
        if enable_voice_output and response.message:
            audio_data = await voice_manager.text_to_speech(
                text=response.message,
                voice=voice,
                speed=speed
            )
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "message": response.message,
            "audio": audio_base64,
            "transcription": transcription,
            "conversation_id": conversation_id
        }
