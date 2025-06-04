"""
对话相关数据模型
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import Field
from app.schemas.assistants.base import BaseRequest, BaseResponse, PaginatedResponse


class ConversationCreateRequest(BaseRequest):
    """创建对话请求"""
    assistant_id: int = Field(..., description="助手ID")
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="元数据")


class ConversationUpdateRequest(BaseRequest):
    """更新对话请求"""
    title: Optional[str] = Field(None, max_length=200, description="对话标题")
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseResponse):
    """对话响应"""
    id: int
    assistant_id: int
    user_id: int
    title: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]

    # 额外字段
    message_count: Optional[int] = None
    last_message_at: Optional[datetime] = None


class ConversationListResponse(PaginatedResponse):
    """对话列表响应"""
    items: List[ConversationResponse]


class MessageCreateRequest(BaseRequest):
    """创建消息请求"""
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="元数据")


class MessageResponse(BaseResponse):
    """消息响应"""
    id: int
    conversation_id: int
    role: str  # "user" or "assistant"
    content: str
    metadata: Dict[str, Any]
    created_at: datetime


class ConversationWithMessagesResponse(ConversationResponse):
    """包含消息的对话响应"""
    messages: List[MessageResponse]