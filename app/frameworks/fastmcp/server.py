"""
FastMCP服务器管理模块
负责创建和管理MCP服务器实例
"""

import logging
from typing import Dict, Any, Optional, List
from fastmcp import FastMCP
from app.config import settings

logger = logging.getLogger(__name__)

# 全局MCP服务器实例
_mcp_server = None


def create_mcp_server(name: str = "智政知识库MCP服务",
                     description: Optional[str] = None,
                     dependencies: Optional[List[str]] = None) -> FastMCP:
    """
    创建MCP服务器实例
    
    参数:
        name: MCP服务器名称
        description: MCP服务器描述
        dependencies: 依赖列表
        
    返回:
        FastMCP实例
    """
    global _mcp_server
    
    if _mcp_server is not None:
        logger.info("MCP服务器已存在，返回现有实例")
        return _mcp_server
    
    if dependencies is None:
        dependencies = ["fastmcp"]
    
    if description is None:
        description = "智政知识库问答系统的MCP服务，提供问答助手和Agent工具"
    
    try:
        _mcp_server = FastMCP(
            name=name,
            dependencies=dependencies
        )
        
        logger.info(f"成功创建MCP服务器: {name}")
        return _mcp_server
    
    except Exception as e:
        logger.error(f"创建MCP服务器时出错: {str(e)}")
        raise


def get_mcp_server() -> FastMCP:
    """
    获取MCP服务器实例，如果不存在则创建
    
    返回:
        FastMCP实例
    """
    global _mcp_server
    
    if _mcp_server is None:
        return create_mcp_server()
    
    return _mcp_server


def get_server_status() -> Dict[str, Any]:
    """
    获取MCP服务器状态
    
    返回:
        服务器状态信息
    """
    server = get_mcp_server()
    
    # 获取工具和资源列表
    tools = [tool.name for tool in server.tool_registry.values()]
    resources = [resource.uri for resource in server.resource_registry.values()]
    prompts = list(server.prompt_registry.keys())
    
    return {
        "name": server.name,
        "tools_count": len(tools),
        "resources_count": len(resources),
        "prompts_count": len(prompts),
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
        "is_running": True
    }


def restart_server() -> Dict[str, str]:
    """
    重启MCP服务器
    
    返回:
        重启状态
    """
    global _mcp_server
    
    try:
        old_name = "未知"
        if _mcp_server:
            old_name = _mcp_server.name
            _mcp_server = None
        
        new_server = get_mcp_server()
        
        return {
            "status": "success",
            "message": f"成功重启MCP服务器: {old_name} -> {new_server.name}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"重启MCP服务器时出错: {str(e)}"
        }
