"""
服务管理模块
提供服务管理、服务注册、服务发现、MCP集成等服务相关功能的统一接口
"""

from .service_manager import *
from .service_registry import *
from .service_discovery import *
from .decorators import *
from .mcp_registrar import *

__all__ = [
    # 服务管理
    "ServiceManager",
    "get_service_manager",
    "start_service",
    "stop_service",
    "restart_service",
    
    # 服务注册
    "ServiceRegistry",
    "register_service",
    "unregister_service",
    "get_service_info",
    
    # 服务发现
    "ServiceDiscovery",
    "discover_services",
    "find_service",
    "get_service_endpoints",
    
    # 装饰器
    "service_endpoint",
    "require_service",
    "circuit_breaker",
    
    # MCP注册器
    "MCPRegistrar",
    "register_mcp_service",
    "get_mcp_services"
]
