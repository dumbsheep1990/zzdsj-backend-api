"""
统一消息中心模块
提供标准化的消息定义、处理和路由功能
"""

from app.messaging.core.models import MessageType, MessageRole, Message
from app.messaging.services.message_service import MessageService, get_message_service

__all__ = [
    'MessageType', 'MessageRole', 'Message',
    'MessageService', 'get_message_service'
]
