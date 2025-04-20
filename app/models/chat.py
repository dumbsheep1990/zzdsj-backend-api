from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.models.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"))
    user_id = Column(String(255), nullable=True)  # Optional user identifier
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    metadata = Column(JSON, default={})
    
    # Relationships
    assistant = relationship("Assistant", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(50))  # user, assistant, system
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    metadata = Column(JSON, default={})
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    references = relationship("MessageReference", back_populates="message")

class MessageReference(Base):
    __tablename__ = "message_references"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    document_chunk_id = Column(Integer, ForeignKey("document_chunks.id"))
    relevance_score = Column(Float)
    
    # Relationships
    message = relationship("Message", back_populates="references")
    document_chunk = relationship("DocumentChunk")
