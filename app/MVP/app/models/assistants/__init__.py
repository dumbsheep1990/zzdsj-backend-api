"""
助手模块数据模型
"""
from .base import BaseModel, TimestampMixin
from .assistant import Assistant, AssistantKnowledgeBase
from .conversation import Conversation, Message, MessageRole
from .qa import (
    QAAssistant,
    Question,
    DocumentSegment,
    QuestionDocumentSegment
)

__all__ = [
    # 基础类
    "BaseModel",
    "TimestampMixin",

    # 助手相关
    "Assistant",
    "AssistantKnowledgeBase",

    # 对话相关
    "Conversation",
    "Message",
    "MessageRole",

    # 问答相关
    "QAAssistant",
    "Question",
    "DocumentSegment",
    "QuestionDocumentSegment"
]
