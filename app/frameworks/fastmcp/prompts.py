"""
FastMCP提示管理模块
负责注册和管理MCP提示
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Union
from fastmcp.prompts.base import Message
from .server import get_mcp_server

logger = logging.getLogger(__name__)

# 提示元数据存储
_prompt_registry = {}


def register_prompt(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    tags: Optional[List[str]] = None
) -> Callable:
    """
    注册MCP提示的装饰器
    
    参数:
        name: 提示名称，如果不提供则使用函数名
        description: 提示描述，如果不提供则使用函数文档字符串
        category: 提示类别，用于分组展示
        tags: 提示标签，用于筛选
        
    返回:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        nonlocal name, description
        
        # 使用函数名作为默认名称
        if name is None:
            name = func.__name__
        
        # 使用函数文档作为默认描述
        if description is None and func.__doc__:
            description = func.__doc__.strip()
        elif description is None:
            description = f"{name} - MCP提示"
        
        # 获取MCP服务器实例
        mcp = get_mcp_server()
        
        # 注册为MCP提示
        decorated_func = mcp.prompt()(func)
        
        # 存储提示元数据
        _prompt_registry[name] = {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags or [],
            "function": func,
            "decorated_function": decorated_func
        }
        
        logger.info(f"注册MCP提示: {name}")
        return decorated_func
    
    return decorator


def list_prompts(category: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出已注册的MCP提示
    
    参数:
        category: 可选，按类别筛选
        tag: 可选，按标签筛选
        
    返回:
        提示列表
    """
    prompts = []
    
    for prompt_name, prompt_data in _prompt_registry.items():
        # 按类别筛选
        if category and prompt_data["category"] != category:
            continue
        
        # 按标签筛选
        if tag and tag not in prompt_data["tags"]:
            continue
        
        # 添加到结果列表
        prompts.append({
            "name": prompt_data["name"],
            "description": prompt_data["description"],
            "category": prompt_data["category"],
            "tags": prompt_data["tags"]
        })
    
    return prompts


def get_prompt(name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定名称的提示详情
    
    参数:
        name: 提示名称
        
    返回:
        提示详情，如果不存在则返回None
    """
    return _prompt_registry.get(name)
