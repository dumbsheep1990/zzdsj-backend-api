"""
认证授权模块
提供JWT处理、用户认证、权限验证等认证授权功能的统一接口

重构后的模块结构:
- core: 核心基类和异常定义
- jwt: JWT令牌处理
- permissions: 权限管理
"""

import logging

# 核心组件
from .core import *

# 可用模块列表
available_modules = ["core"]

# 安全导入其他模块
try:
    from .jwt import *
    available_modules.append("jwt")
except ImportError as e:
    logging.warning(f"Auth JWT模块导入失败: {e}")

try:
    from .permissions import *
    available_modules.append("permissions")
except ImportError as e:
    logging.warning(f"Auth Permissions模块导入失败: {e}")

__all__ = [
    # 核心组件
    "AuthComponent",
    "UserInfo",
    "AuthStatus",
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "TokenError",
    "TokenExpiredError",
    "InvalidCredentialsError",
    "UserNotFoundError",
    "PermissionDeniedError",
]

# 条件性添加可选模块的导出
if "jwt" in available_modules:
    __all__.extend([
        # JWT处理
        "JWTHandler",
        "create_access_token",
        "verify_token",
        "decode_token",
        "get_current_user",
        "authenticate_user",
        "check_permissions", 
        "require_auth",
        "get_password_hash",
        "verify_password"
    ])

if "permissions" in available_modules:
    __all__.extend([
        # 权限管理 (如果有)
        # "PermissionManager", 
        # "check_resource_permission"
    ])
