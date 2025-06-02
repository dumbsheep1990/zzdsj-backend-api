"""
Services核心模块
提供服务管理的基础类和接口
"""

from .base import ServiceComponent, ServiceInfo, ServiceStatus
from .exceptions import (
    ServiceError,
    ServiceNotFoundError,
    ServiceInitializationError,
    ServiceStartupError,
    ServiceStopError,
    ServiceDiscoveryError,
    ServiceRegistrationError,
    ServiceHealthCheckError
)

__all__ = [
    # 基础类
    "ServiceComponent",
    "ServiceInfo", 
    "ServiceStatus",
    
    # 异常类
    "ServiceError",
    "ServiceNotFoundError",
    "ServiceInitializationError",
    "ServiceStartupError",
    "ServiceStopError",
    "ServiceDiscoveryError",
    "ServiceRegistrationError",
    "ServiceHealthCheckError"
] 