"""
问答相关模型
"""
from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Text, Table, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel, Base

# 问题与文档分段的关联表
question_document_segment = Table(
    'question_document_segment',
    Base.metadata,
    Column('question_id', Integer, ForeignKey('questions.id'), primary_key=True),
    Column('document_segment_id', Integer, ForeignKey('document_segments.id'), primary_key=True)
)


class QAAssistant(BaseModel):
    """问答助手模型"""
    __tablename__ = "qa_assistants"

    # 基本信息
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500))
    type = Column(String(50), default="standard")
    icon = Column(String(200))
    status = Column(String(20), default="active", index=True)

    # 配置
    config = Column(JSON, default={})
    knowledge_base_id = Column(Integer, ForeignKey('knowledge_bases.id'))

    # 权限
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    is_public = Column(Boolean, default=False, index=True)

    # 关系
    owner = relationship("User")
    knowledge_base = relationship("KnowledgeBase")
    questions = relationship("Question", back_populates="assistant", cascade="all, delete-orphan")


class Question(BaseModel):
    """问题模型"""
    __tablename__ = "questions"

    # 基本信息
    assistant_id = Column(Integer, ForeignKey('qa_assistants.id'), nullable=False, index=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), index=True)

    # 统计信息
    views_count = Column(Integer, default=0)

    # 元数据
    meta_data = Column(JSON, default={})

    # 创建者
    created_by = Column(Integer, ForeignKey('users.id'))

    # 关系
    assistant = relationship("QAAssistant", back_populates="questions")
    document_segments = relationship(
        "DocumentSegment",
        secondary=question_document_segment,
        back_populates="questions"
    )
    creator = relationship("User")


class DocumentSegment(BaseModel):
    """文档分段模型"""
    __tablename__ = "document_segments"

    # 基本信息
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False, index=True)
    content = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)

    # 元数据
    meta_data = Column(JSON, default=lambda: {})

    # 关系
    document = relationship("Document", back_populates="segments")
    questions = relationship(
        "Question",
        secondary=question_document_segment,
        back_populates="document_segments"
    )


class QuestionDocumentSegment(BaseModel):
    """问题与文档分段关联模型（用于存储额外信息）"""
    __tablename__ = "question_document_segment_extra"

    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    document_segment_id = Column(Integer, ForeignKey('document_segments.id'), nullable=False)
    relevance_score = Column(Integer, default=100)

    # 关系
    question = relationship("Question")
    document_segment = relationship("DocumentSegment")