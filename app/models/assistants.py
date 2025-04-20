from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.database import Base

class Assistant(Base):
    """
    助手模型，表示系统中的AI助手及其能力
    """
    __tablename__ = "assistants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    model_id = Column(String(50), default="gpt-4")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    capabilities = Column(JSON, default={"customer_support": True, "question_answering": True, "service_intro": True})
    
    # 关系
    knowledge_bases = relationship("AssistantKnowledgeBase", back_populates="assistant")
    conversations = relationship("Conversation", back_populates="assistant")

class AssistantKnowledgeBase(Base):
    """
    助手-知识库关联模型，建立助手与知识库之间的关系
    """
    __tablename__ = "assistant_knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"))
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"))
    
    # 关系
    assistant = relationship("Assistant", back_populates="knowledge_bases")
    knowledge_base = relationship("KnowledgeBase", back_populates="assistants")
