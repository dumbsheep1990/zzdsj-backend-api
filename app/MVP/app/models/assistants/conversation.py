"""
对话相关模型
"""
from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship
import enum
from app.models.assistants.base import BaseModel


class MessageRole(enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(BaseModel):
    """对话模型"""
    __tablename__ = "conversations"

    # 基本信息
    assistant_id = Column(Integer, ForeignKey('assistants.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(200), nullable=False)

    # 元数据
    metadata = Column(JSON, default={})

    # 关系
    assistant = relationship("Assistant", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(BaseModel):
    """消息模型"""
    __tablename__ = "messages"

    # 基本信息
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False, index=True)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # 元数据
    metadata = Column(JSON, default={})

    # 关系
    conversation = relationship("Conversation", back_populates="messages")
