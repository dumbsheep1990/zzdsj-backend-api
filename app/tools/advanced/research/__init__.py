"""
研究工具模块
提供深度研究功能的高级工具实现
"""

from app.tools.advanced.research.deep_research import get_deep_research_tool
from app.tools.advanced.research.deep_research_service import DeepResearchService

__all__ = [
    "get_deep_research_tool",
    "DeepResearchService"
]
