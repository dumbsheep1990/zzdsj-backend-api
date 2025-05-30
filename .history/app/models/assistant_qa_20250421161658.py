"""
问答助手数据模型
定义与问答助手、问题卡片和文档关联相关的数据库模型
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, Float, Text, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.database import Base


class AnswerMode(str, enum.Enum):
    """回答模式枚举"""
    DEFAULT = "default"       # 默认模式
    DOCS_ONLY = "docs_only"   # 仅从文档回答
    MODEL_ONLY = "model_only" # 仅使用模型回答
    HYBRID = "hybrid"         # 混合模式


class Assistant(Base):
    """问答助手模型"""
    __tablename__ = "assistants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)  # 产品文档助手、技术支持助手等
    icon = Column(String(255), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    config = Column(JSON, nullable=True)  # 助手特定配置
    
    # 与此助手关联的问题集
    questions = relationship("Question", back_populates="assistant", cascade="all, delete-orphan")
    
    # 与此助手关联的知识库
    knowledge_base_id = Column(Integer, ForeignKey("knowledge_bases.id"), nullable=True)
    knowledge_base = relationship("KnowledgeBase")


class Question(Base):
    """问题模型"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    assistant_id = Column(Integer, ForeignKey("assistants.id"))
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    views_count = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    
    # 回答设置
    answer_mode = Column(String(20), default=AnswerMode.DEFAULT)
    use_cache = Column(Boolean, default=True)
    
    # 关系
    assistant = relationship("Assistant", back_populates="questions")
    document_segments = relationship("QuestionDocumentSegment", back_populates="question", cascade="all, delete-orphan")


class QuestionDocumentSegment(Base):
    """问题与文档分段的关联模型"""
    __tablename__ = "question_document_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    segment_id = Column(Integer, ForeignKey("document_segments.id"))
    relevance_score = Column(Float, default=0.0)  # 相关度分数
    is_enabled = Column(Boolean, default=True)  # 是否启用此分段
    
    # 关系
    question = relationship("Question", back_populates="document_segments")
    document = relationship("Document")
    segment = relationship("DocumentSegment")
