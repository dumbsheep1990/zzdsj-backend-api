"""
助手相关模型
"""
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from app.models.assistants.base import BaseModel

# 助手与知识库的关联表
assistant_knowledge_base = Table(
    'assistant_knowledge_base',
    BaseModel.metadata,
    Column('assistant_id', Integer, ForeignKey('assistants.id'), primary_key=True),
    Column('knowledge_base_id', Integer, ForeignKey('knowledge_bases.id'), primary_key=True)
)


class Assistant(BaseModel):
    """AI助手模型"""
    __tablename__ = "assistants"

    # 基本信息
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500))
    model = Column(String(50), nullable=False)
    system_prompt = Column(Text)

    # 配置信息
    capabilities = Column(ARRAY(String), default=[])
    category = Column(String(50), index=True)
    tags = Column(ARRAY(String), default=[])
    avatar_url = Column(String(500))
    config = Column(JSON, default={})

    # 权限信息
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    is_public = Column(Boolean, default=False, index=True)
    is_active = Column(Boolean, default=True, index=True)

    # 关系
    owner = relationship("User", back_populates="assistants")
    conversations = relationship("Conversation", back_populates="assistant", cascade="all, delete-orphan")
    knowledge_bases = relationship(
        "KnowledgeBase",
        secondary=assistant_knowledge_base,
        back_populates="assistants"
    )


class AssistantKnowledgeBase(BaseModel):
    """助手与知识库关联模型（用于存储额外信息）"""
    __tablename__ = "assistant_knowledge_base_extra"

    assistant_id = Column(Integer, ForeignKey('assistants.id'), nullable=False)
    knowledge_base_id = Column(Integer, ForeignKey('knowledge_bases.id'), nullable=False)
    priority = Column(Integer, default=0)
    config = Column(JSON, default={})

    # 关系
    assistant = relationship("Assistant")
    knowledge_base = relationship("KnowledgeBase")
