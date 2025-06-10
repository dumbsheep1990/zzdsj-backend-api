"""
搜索工具模块
提供Web搜索和相关搜索功能的工具实现
支持LlamaIndex和Agno两种实现方式
"""

# LlamaIndex版本工具（保持向后兼容）
from app.tools.base.search.search_tool import (
    get_search_tool,
    create_search_function_tool,
    WebSearchTool
)

# Agno版本工具（推荐使用）
from app.tools.base.search.agno_search_tool import (
    AgnoWebSearchTool,
    AgnoSearchQuery,
    AgnoSearchResult,
    create_agno_web_search_tool,
    get_agno_search_tool,
    AgnoSearchToolWrapper
)

__all__ = [
    # LlamaIndex版本（向后兼容）
    "get_search_tool",
    "create_search_function_tool",
    "WebSearchTool",
    
    # Agno版本（推荐）
    "AgnoWebSearchTool",
    "AgnoSearchQuery",
    "AgnoSearchResult",
    "create_agno_web_search_tool",
    "get_agno_search_tool",
    "AgnoSearchToolWrapper"
]
