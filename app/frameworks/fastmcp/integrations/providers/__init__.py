"""
第三方MCP服务提供商模块
包含各种MCP服务提供商的具体实现
"""

from importlib import import_module
from typing import Dict, Any, Optional

def get_provider_module(provider: str) -> Optional[Any]:
    """
    获取提供商模块
    
    参数:
        provider: 提供商名称
        
    返回:
        提供商模块或None
    """
    try:
        return import_module(f"app.frameworks.fastmcp.integrations.providers.{provider}")
    except ImportError:
        try:
            return import_module("app.frameworks.fastmcp.integrations.providers.generic")
        except ImportError:
            return None
