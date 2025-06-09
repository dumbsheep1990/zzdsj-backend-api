"""
数据模型包
"""
from .assistants.base import BaseModel, TimestampMixin
from .user import User
from .knowledge_base import KnowledgeBase, Document
from .assistants import *

__all__ = [
    # 基础类
    "BaseModel",
    "TimestampMixin",

    # 用户相关
    "User",

    # 知识库相关
    "KnowledgeBase",
    "Document",

    # 助手相关
    "Assistant",
    "AssistantKnowledgeBase",
    "Conversation",
    "Message",
    "MessageRole",
    "QAAssistant",
    "Question",
    "DocumentSegment",
    "QuestionDocumentSegment"
]