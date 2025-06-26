"""
助手模型模块: AI助手、对话和消息的数据库模型
现已扩展支持Agno框架特有功能
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Table, Boolean
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
    现已扩展支持Agno框架配置
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
    
    # Agno框架特有字段
    framework = Column(String(50), nullable=False, default='general')  # 'general', 'agno', 'owl', 'llamaindex', etc.
    agno_config = Column(JSON, nullable=True)  # Agno特有配置
    agno_agent_id = Column(String(255), nullable=True)  # Agno Agent实例ID
    is_agno_managed = Column(Boolean, default=False)  # 是否由Agno框架管理
    
    # 关系
    knowledge_bases = relationship(
        "KnowledgeBase",
        secondary=assistant_knowledge_base,
        back_populates="assistants"
    )
    conversations = relationship("Conversation", back_populates="assistant", cascade="all, delete-orphan")
    agno_sessions = relationship("AgnoSession", back_populates="assistant", cascade="all, delete-orphan")
    orchestrations = relationship("AgentOrchestration", back_populates="assistant", cascade="all, delete-orphan")
    
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
            "knowledge_base_ids": [kb.id for kb in self.knowledge_bases] if self.knowledge_bases else [],
            # Agno特有字段
            "framework": self.framework,
            "agno_config": self.agno_config,
            "agno_agent_id": self.agno_agent_id,
            "is_agno_managed": self.is_agno_managed
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


class UserAgnoConfig(Base):
    """
    用户级Agno配置模型
    存储每个用户的个性化Agno配置
    """
    __tablename__ = "user_agno_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    config_data = Column(JSON, nullable=False)  # 完整的Agno配置数据
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为API响应的字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "config_data": self.config_data,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AgnoSession(Base):
    """
    Agno会话模型
    跟踪Agno Agent的会话状态和内存
    """
    __tablename__ = "agno_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False)
    
    # Agno特有状态
    memory_data = Column(JSON, nullable=True)  # Agent内存数据
    tool_states = Column(JSON, nullable=True)  # 工具状态
    session_metadata = Column(JSON, nullable=True)  # 会话元数据
    
    # 状态管理
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    assistant = relationship("Assistant", back_populates="agno_sessions")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为API响应的字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "assistant_id": self.assistant_id,
            "user_id": self.user_id,
            "agent_name": self.agent_name,
            "memory_data": self.memory_data,
            "tool_states": self.tool_states,
            "session_metadata": self.session_metadata,
            "is_active": self.is_active,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AgnoToolExecution(Base):
    """
    Agno工具执行记录模型
    跟踪工具调用历史和性能
    """
    __tablename__ = "agno_tool_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("agno_sessions.session_id"), nullable=False)
    tool_name = Column(String(255), nullable=False)
    tool_id = Column(String(255), nullable=False)
    
    # 执行详情
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    
    # 时间戳
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为API响应的字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
