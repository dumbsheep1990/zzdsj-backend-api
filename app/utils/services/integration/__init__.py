"""
服务集成子模块
提供外部服务集成功能，如MCP等
"""

from .mcp_integration import *

__all__ = [
    "MCPRegistrar",
    "register_mcp_service",
    "get_mcp_services"
] 