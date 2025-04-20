"""
助手模型模块: AI助手、对话和消息的数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import List, Dict, Any, Optional

from app.models.database import Base

# 助手和知识库之间多对多关系的关联表
assistant_knowledge_base = Table(
    'assistant_knowledge_base',
    Base.metadata,
    Column('assistant_id', Integer, ForeignKey('assistants.id'), primary_key=True),
    Column('knowledge_base_id', Integer, ForeignKey('knowledge_bases.id'), primary_key=True)
)

class Assistant(Base):
    """
    助手模型，表示具有特定能力和知识库连接的AI助手
    """
    __tablename__ = "assistants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)  # 能力字符串列表
    configuration = Column(JSON, nullable=True)  # 助手特定配置
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    access_url = Column(String(255), nullable=True)  # 访问此助手web界面的URL
    
    # 关系
    knowledge_bases = relationship(
        "KnowledgeBase",
        secondary=assistant_knowledge_base,
        back_populates="assistants"
    )
    conversations = relationship("Conversation", back_populates="assistant", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为API响应的字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "capabilities": self.capabilities,
            "configuration": self.configuration,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "access_url": self.access_url,
            "knowledge_base_ids": [kb.id for kb in self.knowledge_bases] if self.knowledge_bases else []
        }


class Conversation(Base):
    """
    对话模型，表示与助手的聊天会话
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    metadata = Column(JSON, nullable=True)  # 关于对话的任意元数据
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # 关系
    assistant = relationship("Assistant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为API响应的字典"""
        return {
            "id": self.id,
            "assistant_id": self.assistant_id,
            "title": self.title,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": len(self.messages) if self.messages else 0
        }


class Message(Base):
    """
    消息模型，表示对话中的单条消息
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)  # 消息元数据，包括来源、处理状态等
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为API响应的字典"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
