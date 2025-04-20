"""
Assistant Models Module: Database models for AI assistants, conversations, and messages
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import List, Dict, Any, Optional

from app.models.database import Base

# Association table for many-to-many relationship between assistants and knowledge bases
assistant_knowledge_base = Table(
    'assistant_knowledge_base',
    Base.metadata,
    Column('assistant_id', Integer, ForeignKey('assistants.id'), primary_key=True),
    Column('knowledge_base_id', Integer, ForeignKey('knowledge_bases.id'), primary_key=True)
)

class Assistant(Base):
    """
    Assistant model representing an AI assistant with specific capabilities
    and knowledge base connections
    """
    __tablename__ = "assistants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)  # List of capability strings
    configuration = Column(JSON, nullable=True)  # Assistant-specific configuration
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    access_url = Column(String(255), nullable=True)  # URL for accessing this assistant's web interface
    
    # Relationships
    knowledge_bases = relationship(
        "KnowledgeBase",
        secondary=assistant_knowledge_base,
        back_populates="assistants"
    )
    conversations = relationship("Conversation", back_populates="assistant", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
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
    Conversation model representing a chat session with an assistant
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    metadata = Column(JSON, nullable=True)  # Arbitrary metadata about the conversation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relationships
    assistant = relationship("Assistant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
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
    Message model representing a single message in a conversation
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)  # Message metadata, including sources, processing status, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
