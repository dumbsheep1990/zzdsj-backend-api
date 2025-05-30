from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import BackgroundTasks, HTTPException, UploadFile
import base64

from app.utils.service_decorators import register_service

# 导入核心业务逻辑层
from app.core.chat.conversation_manager import ConversationManager

from app.models.chat import Conversation, Message, MessageReference
from app.models.assistants import Assistant
from core.voice.voice_manager import VoiceAgentManager
from app.schemas.chat import (
    ConversationCreate, 
    ConversationUpdate, 
    Conversation as ConversationSchema,
    MessageCreate,
    ChatRequest,
    ChatResponse
)
from core.chat.chat_service import process_chat_request

@register_service(service_type="chat", priority="high", description="聊天交互服务")
class ChatService:
    """
    聊天服务层，管理对话和消息的业务逻辑。
    已重构为使用核心业务逻辑层，遵循分层架构原则。
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # 使用核心业务逻辑层
        self.conversation_manager = ConversationManager(db)
        
    async def get_conversations(self, assistant_id: Optional[int] = None, 
                               user_id: Optional[str] = None, 
                               skip: int = 0, 
                               limit: int = 100) -> List[Conversation]:
        """
        获取会话列表，支持按助手ID和用户ID过滤
        """
        try:
            if assistant_id and user_id:
                # 获取特定助手和用户的对话
                result = await self.conversation_manager.list_assistant_conversations(
                    str(assistant_id), user_id, skip, limit
                )
            elif user_id:
                # 获取用户的所有对话
                result = await self.conversation_manager.list_user_conversations(
                    user_id, skip, limit
                )
            elif assistant_id:
                # 获取助手的所有对话
                result = await self.conversation_manager.list_assistant_conversations(
                    str(assistant_id), None, skip, limit
                )
            else:
                # 如果没有过滤条件，返回空列表（避免返回所有对话）
                return []
            
            if not result["success"]:
                return []
            
            # 转换为旧的数据模型格式（兼容性）
            conversations = []
            for conv_data in result["data"]["conversations"]:
                conversation = Conversation(
                    id=int(conv_data["id"]) if conv_data["id"].isdigit() else hash(conv_data["id"]) % 2147483647,
                    assistant_id=int(conv_data["assistant_id"]),
                    user_id=conv_data["user_id"],
                    title=conv_data["title"],
                    metadata=conv_data.get("metadata", {}),
                    created_at=conv_data["created_at"],
                    updated_at=conv_data["updated_at"]
                )
                conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            # 如果核心层调用失败，返回空列表
            return []
    
    async def create_conversation(self, conversation_data: ConversationCreate) -> Conversation:
        """
        创建新会话
        """
        try:
            # 使用核心层创建对话
            result = await self.conversation_manager.create_conversation(
                str(conversation_data.assistant_id),
                conversation_data.user_id,
                conversation_data.title,
                conversation_data.metadata
            )
            
            if not result["success"]:
                if result.get("error_code") == "ASSISTANT_NOT_FOUND":
                    raise HTTPException(status_code=404, detail="未找到助手")
                else:
                    raise HTTPException(status_code=500, detail=result["error"])
            
            # 转换为旧的数据模型格式（兼容性）
            conv_data = result["data"]
            conversation = Conversation(
                id=int(conv_data["id"]) if conv_data["id"].isdigit() else hash(conv_data["id"]) % 2147483647,
                assistant_id=int(conv_data["assistant_id"]),
                user_id=conv_data["user_id"],
                title=conv_data["title"],
                metadata=conv_data.get("metadata", {}),
                created_at=conv_data["created_at"],
                updated_at=conv_data["updated_at"]
            )
            
            return conversation
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")
    
    async def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """
        通过ID获取会话及消息
        """
        try:
            # 使用核心层获取对话
            result = await self.conversation_manager.get_conversation(str(conversation_id))
            
            if not result["success"]:
                return None
            
            # 转换为旧的数据模型格式（兼容性）
            conv_data = result["data"]
            conversation = Conversation(
                id=int(conv_data["id"]) if conv_data["id"].isdigit() else hash(conv_data["id"]) % 2147483647,
                assistant_id=int(conv_data["assistant_id"]),
                user_id=conv_data["user_id"],
                title=conv_data["title"],
                metadata=conv_data.get("metadata", {}),
                created_at=conv_data["created_at"],
                updated_at=conv_data["updated_at"]
            )
            
            return conversation
            
        except Exception as e:
            return None
    
    async def update_conversation(self, conversation_id: int, conversation_data: ConversationUpdate) -> Optional[Conversation]:
        """
        更新会话信息
        """
        try:
            # 准备更新数据
            update_data = conversation_data.dict(exclude_unset=True)
            
            # 使用核心层更新对话
            result = await self.conversation_manager.update_conversation(str(conversation_id), update_data)
            
            if not result["success"]:
                return None
            
            # 转换为旧的数据模型格式（兼容性）
            conv_data = result["data"]
            conversation = Conversation(
                id=int(conv_data["id"]) if conv_data["id"].isdigit() else hash(conv_data["id"]) % 2147483647,
                assistant_id=int(conv_data["assistant_id"]),
                user_id=conv_data["user_id"],
                title=conv_data["title"],
                metadata=conv_data.get("metadata", {}),
                created_at=conv_data["created_at"],
                updated_at=conv_data["updated_at"]
            )
            
            return conversation
            
        except Exception as e:
            return None
    
    async def delete_conversation(self, conversation_id: int) -> bool:
        """
        删除会话及关联的消息
        """
        try:
            # 使用核心层删除对话
            result = await self.conversation_manager.delete_conversation(str(conversation_id))
            return result["success"]
            
        except Exception as e:
            return False
    
    async def create_message(self, message_data: MessageCreate) -> Message:
        """
        创建新消息
        """
        try:
            # 使用核心层添加消息
            result = await self.conversation_manager.add_message(
                str(message_data.conversation_id),
                message_data.role,
                message_data.content,
                message_data.metadata
            )
            
            if not result["success"]:
                if result.get("error_code") == "CONVERSATION_NOT_FOUND":
                    raise HTTPException(status_code=404, detail="未找到会话")
                else:
                    raise HTTPException(status_code=500, detail=result["error"])
            
            # 转换为旧的数据模型格式（兼容性）
            msg_data = result["data"]
            message = Message(
                id=int(msg_data["id"]) if str(msg_data["id"]).isdigit() else hash(str(msg_data["id"])) % 2147483647,
                conversation_id=int(msg_data["conversation_id"]) if str(msg_data["conversation_id"]).isdigit() else hash(str(msg_data["conversation_id"])) % 2147483647,
                role=msg_data["role"],
                content=msg_data["content"],
                metadata=msg_data.get("metadata", {}),
                created_at=msg_data["created_at"],
                updated_at=msg_data["updated_at"]
            )
            
            return message
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建消息失败: {str(e)}")
    
    async def process_chat(self, chat_request: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
        """
        处理聊天请求并获取响应
        """
        try:
            # 检查会话是否存在（如果提供了会话ID）
            if chat_request.conversation_id:
                conversation_result = await self.conversation_manager.get_conversation(str(chat_request.conversation_id))
                if not conversation_result["success"]:
                    raise HTTPException(status_code=404, detail="未找到会话")
            
            # 检查助手是否存在（直接查询数据库，因为助手管理不在当前核心层范围内）
            assistant = self.db.query(Assistant).filter(Assistant.id == chat_request.assistant_id).first()
            if not assistant:
                raise HTTPException(status_code=404, detail="未找到助手")
            
            # 创建或使用现有会话
            if not chat_request.conversation_id:
                # 创建新会话
                create_result = await self.conversation_manager.create_conversation(
                    str(chat_request.assistant_id),
                    chat_request.user_id,
                    chat_request.message[:30] + "..." if len(chat_request.message) > 30 else chat_request.message
                )
                
                if not create_result["success"]:
                    raise HTTPException(status_code=500, detail="创建会话失败")
                
                # 获取新创建的会话ID
                conversation_id = create_result["data"]["id"]
                chat_request.conversation_id = int(conversation_id) if conversation_id.isdigit() else hash(conversation_id) % 2147483647
            
            # 创建用户消息
            message_result = await self.conversation_manager.add_message(
                str(chat_request.conversation_id),
                "user",
                chat_request.message,
                chat_request.metadata
            )
            
            if not message_result["success"]:
                raise HTTPException(status_code=500, detail="创建用户消息失败")
            
            user_message_id = message_result["data"]["id"]
            user_message_id = int(user_message_id) if str(user_message_id).isdigit() else hash(str(user_message_id)) % 2147483647
            
            # 处理聊天请求
            response = await process_chat_request(
                db=self.db,
                assistant=assistant,
                conversation_id=chat_request.conversation_id,
                message=chat_request.message,
                message_id=user_message_id,
                user_id=chat_request.user_id,
                metadata=chat_request.metadata,
                background_tasks=background_tasks
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"处理聊天请求失败: {str(e)}")
    
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
        try:
            # 检查助手是否存在（直接查询数据库，因为助手管理不在当前核心层范围内）
            assistant = self.db.query(Assistant).filter(Assistant.id == assistant_id).first()
            if not assistant:
                raise HTTPException(status_code=404, detail="未找到助手")
            
            # 如果提供了会话ID，验证它是否存在
            if conversation_id:
                conversation_result = await self.conversation_manager.get_conversation(str(conversation_id))
                if not conversation_result["success"]:
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
                create_result = await self.conversation_manager.create_conversation(
                    str(assistant_id),
                    user_id,
                    final_message[:30] + "..." if len(final_message) > 30 else final_message
                )
                
                if not create_result["success"]:
                    raise HTTPException(status_code=500, detail="创建会话失败")
                
                conversation_id_str = create_result["data"]["id"]
                conversation_id = int(conversation_id_str) if conversation_id_str.isdigit() else hash(conversation_id_str) % 2147483647
            
            # 创建用户消息
            message_result = await self.conversation_manager.add_message(
                str(conversation_id),
                "user",
                final_message
            )
            
            if not message_result["success"]:
                raise HTTPException(status_code=500, detail="创建用户消息失败")
            
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
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"处理语音聊天失败: {str(e)}")
