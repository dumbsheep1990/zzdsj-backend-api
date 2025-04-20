"""
助手模式模块: 助手API请求和响应的Pydantic模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AssistantCapability(str, Enum):
    """助手能力的枚举类型"""
    TEXT = "text"
    MULTIMODAL = "multimodal"
    VOICE = "voice"
    CODE = "code"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    TOOLS = "tools"


class AssistantBase(BaseModel):
    """具有共同属性的基础助手模式"""
    name: str = Field(..., description="助手名称", max_length=100)
    description: Optional[str] = Field(None, description="助手目的的描述")
    model: str = Field(..., description="助手使用的模型", max_length=100)
    capabilities: List[str] = Field(
        default=["text"],
        description="助手能力列表（文本、多模态、语音等）"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="助手特定配置"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="引导助手行为的系统提示"
    )


class AssistantCreate(AssistantBase):
    """创建新助手的模式"""
    knowledge_base_ids: Optional[List[int]] = Field(
        None,
        description="要与助手关联的知识库ID列表"
    )


class AssistantUpdate(BaseModel):
    """更新助手的模式"""
    name: Optional[str] = Field(None, description="助手名称", max_length=100)
    description: Optional[str] = Field(None, description="助手目的的描述")
    model: Optional[str] = Field(None, description="助手使用的模型", max_length=100)
    capabilities: Optional[List[str]] = Field(
        None,
        description="助手能力列表（文本、多模态、语音等）"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        None,
        description="助手特定配置"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="引导助手行为的系统提示"
    )
    knowledge_base_ids: Optional[List[int]] = Field(
        None,
        description="要与助手关联的知识库ID列表"
    )


class AssistantResponse(AssistantBase):
    """助手响应的模式"""
    id: int
    access_url: Optional[str] = Field(None, description="访问助手Web界面的URL")
    created_at: datetime
    updated_at: Optional[datetime] = None
    knowledge_base_ids: List[int] = Field([], description="关联知识库ID列表")
    
    class Config:
        orm_mode = True


class AssistantList(BaseModel):
    """助手列表的模式"""
    assistants: List[AssistantResponse]
    total: int


class ConversationBase(BaseModel):
    """会话基础模式"""
    title: Optional[str] = Field(None, description="会话标题")
    metadata: Optional[Dict[str, Any]] = Field(None, description="任意元数据")


class ConversationCreate(ConversationBase):
    """创建新会话的模式"""
    pass


class ConversationResponse(ConversationBase):
    """会话响应的模式"""
    id: int
    assistant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = 0
    
    class Config:
        orm_mode = True


class MessageBase(BaseModel):
    """消息基础模式"""
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")


class MessageCreate(MessageBase):
    """创建新消息的模式"""
    pass


class MessageResponse(MessageBase):
    """消息响应的模式"""
    id: int
    conversation_id: int
    role: str
    created_at: datetime
    
    class Config:
        orm_mode = True


class AssistantSummary(BaseModel):
    """助手摘要模式"""
    id: int
    name: str
    description: Optional[str] = None
    capabilities: List[str]
    model: str
    access_url: Optional[str] = None
    
    class Config:
        orm_mode = True


class ApiKeyCreate(BaseModel):
    """创建API密钥的模式"""
    name: str = Field(..., description="API密钥名称")
    assistant_id: Optional[int] = Field(None, description="可选地限制密钥到特定助手")
    expires_at: Optional[datetime] = Field(None, description="可选地设置过期日期")


class ApiKeyResponse(BaseModel):
    """API密钥响应的模式"""
    id: int
    name: str
    key: str
    assistant_id: Optional[int] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
