"""
认证和权限服务模块
负责用户管理和权限控制
"""

from .user_service import UserService
from .permission_service import ResourcePermissionService

__all__ = [
    "UserService",
    "ResourcePermissionService"
]