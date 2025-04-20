from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.models.database import Base

class KnowledgeBase(Base):
    """
    知识库模型，表示一个包含多个文档的知识集合
    """
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    settings = Column(JSON, default={})
    type = Column(String(50), default="default")  # default, csv, pdf, web等
    agno_kb_id = Column(String(255), nullable=True)  # Agno知识库ID
    total_documents = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    embedding_model = Column(String(100), default="text-embedding-ada-002")
    
    # 关系
    documents = relationship("Document", back_populates="knowledge_base")
    assistants = relationship("AssistantKnowledgeBase", back_populates="knowledge_base")

class Document(Base):
    """
    文档模型，表示知识库中的单个文档
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"))
    title = Column(String(255), nullable=False)
    content = Column(Text)
    mime_type = Column(String(100), default="text/plain")
    metadata = Column(JSON, default={})
    file_path = Column(String(255))
    file_size = Column(Integer, default=0)  # 大小（字节）
    status = Column(String(50), default="pending")  # pending, processing, indexed, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")

class DocumentChunk(Base):
    """
    文档块模型，表示文档的分段部分，用于嵌入和检索
    """
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    content = Column(Text)
    metadata = Column(JSON, default={})
    embedding_id = Column(String(255))
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    document = relationship("Document", back_populates="chunks")

class AssistantKnowledgeBase(Base):
    """
    助手-知识库关联模型，表示助手和知识库之间的多对多关系
    """
    __tablename__ = "assistant_knowledge_bases"
    
    assistant_id = Column(Integer, ForeignKey("assistants.id"), primary_key=True)
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    assistant = relationship("Assistant", back_populates="knowledge_bases")
    knowledge_base = relationship("KnowledgeBase", back_populates="assistants")
