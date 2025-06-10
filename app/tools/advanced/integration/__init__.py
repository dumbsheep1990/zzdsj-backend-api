"""
集成工具模块
提供模型与工具集成的高级功能实现
"""

from .chat_with_tools import ChatWithTools, create_chat_with_tools
from .agno_chat_with_tools import (
    AgnoChatWithTools, 
    AgnoToolCall, 
    AgnoToolRegistry,
    create_agno_chat_with_tools,
    get_agno_chat_with_tools
)

__all__ = [
    # LlamaIndex版本（保持向后兼容）
    "ChatWithTools",
    "create_chat_with_tools",
    
    # Agno原生版本（推荐使用）
    "AgnoChatWithTools",
    "AgnoToolCall", 
    "AgnoToolRegistry",
    "create_agno_chat_with_tools",
    "get_agno_chat_with_tools",
]
