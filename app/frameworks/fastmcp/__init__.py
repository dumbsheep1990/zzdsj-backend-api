"""
FastMCP框架集成模块
提供MCP(Model Context Protocol)服务功能的支持
"""

# 自定义MCP服务
from .server import create_mcp_server, get_mcp_server
from .tools import register_tool, list_tools
from .resources import register_resource, list_resources
from .prompts import register_prompt, list_prompts

# 第三方MCP服务集成
from .integrations import (
    register_external_mcp, 
    list_external_mcps, 
    get_external_mcp,
    MCPClient, 
    create_mcp_client
)

__all__ = [
    # 自定义MCP服务
    "create_mcp_server",
    "get_mcp_server",
    "register_tool",
    "list_tools",
    "register_resource",
    "list_resources",
    "register_prompt",
    "list_prompts",
    
    # 第三方MCP服务集成
    "register_external_mcp",
    "list_external_mcps",
    "get_external_mcp",
    "MCPClient",
    "create_mcp_client"
]
