from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.models.database import Base

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    settings = Column(JSON, default={})
    type = Column(String(50), default="default")  # default, csv, pdf, web, etc.
    agno_kb_id = Column(String(255), nullable=True)  # Agno knowledge base ID
    total_documents = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    embedding_model = Column(String(100), default="text-embedding-ada-002")
    
    # Relationships
    documents = relationship("Document", back_populates="knowledge_base")
    assistants = relationship("AssistantKnowledgeBase", back_populates="knowledge_base")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"))
    title = Column(String(255), nullable=False)
    content = Column(Text)
    mime_type = Column(String(100), default="text/plain")
    metadata = Column(JSON, default={})
    file_path = Column(String(255))
    file_size = Column(Integer, default=0)  # Size in bytes
    status = Column(String(50), default="pending")  # pending, processing, indexed, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    content = Column(Text)
    metadata = Column(JSON, default={})
    embedding_id = Column(String(255))
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
