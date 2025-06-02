"""
消息队列模块
提供消息队列、消息发布、消息消费等功能的统一接口

重构后的模块结构:
- core: 核心消息组件
- queue: 消息队列实现
"""

import logging

# 可用模块列表
available_modules = []

# 安全导入各个模块
try:
    from .queue import *
    available_modules.append("queue")
except ImportError as e:
    logging.warning(f"Messaging Queue模块导入失败: {e}")

__all__ = []

# 条件性添加可选模块的导出
if "queue" in available_modules:
    __all__.extend([
        # 消息队列
        "MessageQueue",
        "RabbitMQClient", 
        "publish_message",
        "consume_messages",
        "create_queue"
    ])
