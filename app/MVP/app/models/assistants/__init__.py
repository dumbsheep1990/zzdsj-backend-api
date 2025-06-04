"""
助手模块数据模型
"""
from app.models.assistants.base import BaseModel, TimestampMixin
from app.models.assistants.assistant import Assistant, AssistantKnowledgeBase
from app.models.assistants.conversation import Conversation, Message, MessageRole
from app.models.assistants.qa import (
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
