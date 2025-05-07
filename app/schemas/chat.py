from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

# 基础会话模式
class ConversationBase(BaseModel):
    assistant_id: int
    user_id: Optional[str] = None
    title: Optional[str] = "新会话"
    metadata: Optional[Dict[str, Any]] = {}

# 创建会话模式
class ConversationCreate(ConversationBase):
    pass

# 更新会话模式
class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# 会话模式（用于响应）
class Conversation(ConversationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# 消息基础模式
class MessageBase(BaseModel):
    role: str  # 用户、助手、系统
    content: str
    metadata: Optional[Dict[str, Any]] = {}

# 创建消息模式
class MessageCreate(MessageBase):
    conversation_id: int

# 消息模式（用于响应）
class Message(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

# 带消息的会话
class ConversationWithMessages(Conversation):
    messages: List[Message] = []
    
    class Config:
        orm_mode = True

# 引用模式（用于引用信息）
class MessageReference(BaseModel):
    id: int
    message_id: int
    document_chunk_id: int
    relevance_score: float
    
    class Config:
        orm_mode = True

# 聊天请求模式
class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    assistant_id: int
    message: str
    user_id: Optional[str] = None
    enable_voice_input: bool = False
    enable_voice_output: bool = False
    voice: Optional[str] = None
    speed: Optional[float] = None

# 聊天响应模式
class ChatResponse(BaseModel):
    conversation_id: int
    message: Message
    references: Optional[List[Dict[str, Any]]] = None
    audio_data: Optional[str] = None  # 音频数据，Base64编码
    transcription: Optional[Dict[str, Any]] = None  # 语音转录结果
