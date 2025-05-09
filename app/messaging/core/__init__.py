"""
消息核心定义模块
包含消息模型、枚举和基础工具
"""

from app.messaging.core.models import MessageType, MessageRole, Message
from app.messaging.core.formatters import format_to_sse, format_to_json

__all__ = [
    'MessageType', 'MessageRole', 'Message',
    'format_to_sse', 'format_to_json'
]
