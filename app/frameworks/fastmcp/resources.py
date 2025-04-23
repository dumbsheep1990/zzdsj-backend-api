"""
FastMCP资源管理模块
负责注册和管理MCP资源
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Union
from .server import get_mcp_server

logger = logging.getLogger(__name__)

# 资源元数据存储
_resource_registry = {}


def register_resource(
    uri: str,
    description: Optional[str] = None,
    category: str = "general",
    tags: Optional[List[str]] = None
) -> Callable:
    """
    注册MCP资源的装饰器
    
    参数:
        uri: 资源URI标识符
        description: 资源描述，如果不提供则使用函数文档字符串
        category: 资源类别，用于分组展示
        tags: 资源标签，用于筛选
        
    返回:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        nonlocal description
        
        # 使用函数文档作为默认描述
        if description is None and func.__doc__:
            description = func.__doc__.strip()
        elif description is None:
            description = f"{uri} - MCP资源"
        
        # 获取MCP服务器实例
        mcp = get_mcp_server()
        
        # 注册为MCP资源
        decorated_func = mcp.resource(uri)(func)
        
        # 存储资源元数据
        _resource_registry[uri] = {
            "uri": uri,
            "description": description,
            "category": category,
            "tags": tags or [],
            "function": func,
            "decorated_function": decorated_func
        }
        
        logger.info(f"注册MCP资源: {uri}")
        return decorated_func
    
    return decorator


def list_resources(category: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出已注册的MCP资源
    
    参数:
        category: 可选，按类别筛选
        tag: 可选，按标签筛选
        
    返回:
        资源列表
    """
    resources = []
    
    for uri, resource_data in _resource_registry.items():
        # 按类别筛选
        if category and resource_data["category"] != category:
            continue
        
        # 按标签筛选
        if tag and tag not in resource_data["tags"]:
            continue
        
        # 添加到结果列表
        resources.append({
            "uri": resource_data["uri"],
            "description": resource_data["description"],
            "category": resource_data["category"],
            "tags": resource_data["tags"]
        })
    
    return resources


def get_resource(uri: str) -> Optional[Dict[str, Any]]:
    """
    获取指定URI的资源详情
    
    参数:
        uri: 资源URI
        
    返回:
        资源详情，如果不存在则返回None
    """
    return _resource_registry.get(uri)
