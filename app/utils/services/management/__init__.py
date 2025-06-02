"""
服务管理子模块
提供服务管理器和相关功能
"""

# 从原有文件导入，保持兼容性
from .manager import *

__all__ = [
    "ServiceManager",
    "get_service_manager", 
    "start_service",
    "stop_service",
    "restart_service",
    "register_lightrag_service"
] 