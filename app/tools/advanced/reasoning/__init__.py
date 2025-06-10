"""
推理工具模块
提供思维链、深度研究等推理功能的工具实现
支持LlamaIndex和Agno两种实现方式
"""

# LlamaIndex版本工具（保持向后兼容）
from app.tools.advanced.reasoning.cot_tool import (
    CoTTool,
    get_cot_tool,
    create_cot_function_tool,
    get_all_cot_tools
)

# Agno版本工具（推荐使用）
from app.tools.advanced.reasoning.agno_cot_tool import (
    AgnoCoTTool,
    AgnoCoTRequest,
    AgnoCoTResponse,
    AgnoReasoningToolCollection,
    create_agno_cot_tool,
    get_agno_cot_tool,
    create_agno_reasoning_collection,
    AgnoCoTToolWrapper
)

# 其他推理工具
from app.tools.advanced.reasoning.deep_research import (
    get_deep_research_tool
)

__all__ = [
    # LlamaIndex版本（向后兼容）
    "CoTTool",
    "get_cot_tool", 
    "create_cot_function_tool",
    "get_all_cot_tools",
    
    # Agno版本（推荐）
    "AgnoCoTTool",
    "AgnoCoTRequest",
    "AgnoCoTResponse",
    "AgnoReasoningToolCollection",
    "create_agno_cot_tool",
    "get_agno_cot_tool",
    "create_agno_reasoning_collection",
    "AgnoCoTToolWrapper",
    
    # 其他工具
    "get_deep_research_tool"
]
