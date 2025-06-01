"""
消息队列模块
提供消息队列、事件总线等消息传递功能的统一接口
"""

from .message_queue import *

__all__ = [
    # 消息队列
    "MessageQueue",
    "get_message_queue",
    "publish_message",
    "subscribe_message",
    "create_queue",
    "delete_queue"
]
