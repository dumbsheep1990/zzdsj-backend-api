"""
服务管理模块
提供服务管理、服务注册、服务发现、MCP集成等服务相关功能的统一接口

重构后的模块结构:
- core: 核心基类和异常定义
- management: 服务管理器
- discovery: 服务发现和注册
- integration: 外部服务集成
"""

import logging

# 核心组件
from .core import *

# 服务管理
from .management import *

# 保留原有的装饰器
from .decorators import *

# 可用模块列表
available_modules = ["core", "management", "decorators"]

# 安全导入其他模块
try:
    from .discovery import *
    available_modules.append("discovery")
except ImportError as e:
    logging.warning(f"Services Discovery模块导入失败: {e}")

try:
    from .integration import *
    available_modules.append("integration")
except ImportError as e:
    logging.warning(f"Services Integration模块导入失败: {e}")

__all__ = [
    # 核心组件
    "ServiceComponent",
    "ServiceInfo", 
    "ServiceStatus",
    "ServiceError",
    "ServiceNotFoundError",
    "ServiceInitializationError",
    "ServiceStartupError",
    "ServiceStopError",
    "ServiceDiscoveryError",
    "ServiceRegistrationError",
    "ServiceHealthCheckError",
    
    # 服务管理
    "ServiceManager",
    "get_service_manager",
    "start_service",
    "stop_service",
    "restart_service",
    "register_lightrag_service",
    
    # 装饰器
    "service_endpoint",
    "require_service",
    "circuit_breaker",
]

# 条件性添加可选模块的导出
if "discovery" in available_modules:
    __all__.extend([
        # 服务发现
        "ServiceDiscovery",
        "discover_services", 
        "find_service",
        "get_service_endpoints",
        
        # 服务注册
        "ServiceRegistry",
        "register_service",
        "unregister_service",
        "get_service_info",
    ])

if "integration" in available_modules:
    __all__.extend([
        # MCP集成
        "MCPRegistrar",
        "register_mcp_service",
        "get_mcp_services"
    ])
