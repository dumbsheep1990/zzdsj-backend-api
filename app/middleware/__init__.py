"""
中间件模块
包含各种用于请求处理、功能增强和工具集成的中间件
"""

# 敏感词过滤中间件
from app.middleware.sensitive_word_middleware import SensitiveWordMiddleware

# 搜索工具
from app.middleware.search_tool import get_search_tool, create_search_function_tool, WebSearchTool

# Function Calling 相关组件
from app.middleware.function_calling import (
    FunctionCallingAdapter, 
    FunctionCallingConfig,
    FunctionCallingStrategy,
    create_function_calling_adapter
)

from app.middleware.model_with_tools import ModelWithTools, create_model_with_tools
from app.middleware.chat_with_tools import ChatWithTools, create_chat_with_tools

__all__ = [
    # 敏感词过滤
    "SensitiveWordMiddleware",
    
    # 搜索工具
    "get_search_tool", 
    "create_search_function_tool",
    "WebSearchTool",
    
    # Function Calling
    "FunctionCallingAdapter",
    "FunctionCallingConfig", 
    "FunctionCallingStrategy",
    "create_function_calling_adapter",
    "ModelWithTools",
    "create_model_with_tools",
    "ChatWithTools",
    "create_chat_with_tools"
]
