"""
问答助手数据模型
定义与问答助手、问题卡片和文档关联相关的数据库模型
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, Float, Text, DateTime, Enum, Table
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


# 问题标签关联表
question_tag_relations = Table(
    'question_tag_relations',
    Base.metadata,
    Column('question_id', Integer, ForeignKey('questions.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('question_tags.id', ondelete='CASCADE'), primary_key=True)
)


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
    
    # 新增字段
    category = Column(String(50), comment="问题分类")
    priority = Column(Integer, default=0, comment="问题优先级")
    tags = Column(JSON, default=[], comment="问题标签")
    feedback_score = Column(Float, comment="反馈评分")
    feedback_count = Column(Integer, default=0, comment="反馈数量")
    
    # 回答设置
    answer_mode = Column(String(20), default=AnswerMode.DEFAULT)
    use_cache = Column(Boolean, default=True)
    
    # 关系
    assistant = relationship("Assistant", back_populates="questions")
    document_segments = relationship("QuestionDocumentSegment", back_populates="question", cascade="all, delete-orphan")
    feedback_list = relationship("QuestionFeedback", back_populates="question", cascade="all, delete-orphan")
    tag_relations = relationship("QuestionTag", secondary=question_tag_relations, back_populates="questions")
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "assistant_id": self.assistant_id,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "category": self.category,
            "priority": self.priority,
            "tags": self.tags,
            "feedback_score": self.feedback_score,
            "feedback_count": self.feedback_count,
            "views_count": self.views_count,
            "enabled": self.enabled,
            "answer_mode": self.answer_mode,
            "use_cache": self.use_cache,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class QuestionDocumentSegment(Base):
    """问题与文档分段的关联模型"""
    __tablename__ = "question_document_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    segment_id = Column(Integer, ForeignKey("document_chunks.id"))  # 修正为document_chunks
    relevance_score = Column(Float, default=0.0)  # 相关度分数
    is_enabled = Column(Boolean, default=True)  # 是否启用此分段
    
    # 关系
    question = relationship("Question", back_populates="document_segments")
    document = relationship("Document")
    segment = relationship("DocumentChunk")


class QuestionFeedback(Base):
    """问题反馈模型"""
    __tablename__ = "question_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), comment="用户ID")
    rating = Column(Integer, comment="评分 (1-5)")
    feedback_text = Column(Text, comment="反馈文本")
    is_helpful = Column(Boolean, comment="是否有帮助")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关系
    question = relationship("Question", back_populates="feedback_list")
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "question_id": self.question_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "feedback_text": self.feedback_text,
            "is_helpful": self.is_helpful,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class QuestionTag(Base):
    """问题标签模型"""
    __tablename__ = "question_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, comment="标签名称")
    description = Column(Text, comment="标签描述")
    color = Column(String(7), comment="标签颜色 (HEX格式)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关系
    questions = relationship("Question", secondary=question_tag_relations, back_populates="tag_relations")
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
