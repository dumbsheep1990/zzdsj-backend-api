"""
消息队列子模块
提供消息队列功能
"""

from .message_queue import *

__all__ = [
    "MessageQueue",
    "RabbitMQClient",
    "publish_message",
    "consume_messages",
    "create_queue"
] 