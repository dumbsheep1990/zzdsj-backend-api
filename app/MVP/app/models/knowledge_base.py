"""
知识库相关模型
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from .assistants.base import BaseModel


class KnowledgeBase(BaseModel):
    """知识库模型"""
    __tablename__ = "knowledge_bases"

    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)

    # 关系
    owner = relationship("User")
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    # 添加与助手的多对多关系
    assistants = relationship(
        "Assistant",
        secondary="assistant_knowledge_base",
        back_populates="knowledge_bases"
    )


class Document(BaseModel):
    """文档模型"""
    __tablename__ = "documents"

    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    knowledge_base_id = Column(Integer, ForeignKey('knowledge_bases.id'))

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    segments = relationship("DocumentSegment", back_populates="document", cascade="all, delete-orphan")