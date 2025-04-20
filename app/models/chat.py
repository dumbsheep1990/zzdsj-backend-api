from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.models.database import Base

class Conversation(Base):
    """
    对话模型，表示用户与AI助手之间的完整对话会话
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"))
    user_id = Column(String(255), nullable=True)  # 可选的用户标识符
    title = Column(String(255), default="新对话")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    metadata = Column(JSON, default={})
    
    # 关系
    assistant = relationship("Assistant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")

class Message(Base):
    """
    消息模型，表示对话中的单条消息，可以是用户、助手或系统消息
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(50))  # 用户、助手或系统
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    metadata = Column(JSON, default={})
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    references = relationship("MessageReference", back_populates="message")

class MessageReference(Base):
    """
    消息引用模型，用于将消息与其引用的文档块关联起来，用于知识库检索
    """
    __tablename__ = "message_references"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    document_chunk_id = Column(Integer, ForeignKey("document_chunks.id"))
    relevance_score = Column(Float)
    
    # 关系
    message = relationship("Message", back_populates="references")
    document_chunk = relationship("DocumentChunk")
