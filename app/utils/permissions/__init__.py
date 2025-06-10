"""
权限管理工具模块
提供基于角色的访问控制(RBAC)、细粒度权限管理等功能
"""

from .tool_permission_manager import (
    ToolPermissionManager,
    Permission,
    Role,
    User,
    AccessContext,
    AccessLog,
    PermissionType,
    PermissionScope,
    AccessResult,
    tool_permission_manager
)

__all__ = [
    "ToolPermissionManager",
    "Permission",
    "Role", 
    "User",
    "AccessContext",
    "AccessLog",
    "PermissionType",
    "PermissionScope",
    "AccessResult",
    "tool_permission_manager"
]

__version__ = "1.0.0" 