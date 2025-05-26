"""
搜索工具模块
提供Web搜索和相关搜索功能的工具实现
"""

from app.tools.base.search.search_tool import (
    get_search_tool,
    create_search_function_tool,
    WebSearchTool
)

__all__ = [
    "get_search_tool",
    "create_search_function_tool",
    "WebSearchTool"
]
