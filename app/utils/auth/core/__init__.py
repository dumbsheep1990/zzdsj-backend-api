"""
Auth核心模块
提供认证授权的基础类和接口
"""

from .base import AuthComponent, UserInfo, AuthStatus
from .exceptions import (
    AuthError,
    AuthenticationError,
    AuthorizationError,
    TokenError,
    TokenExpiredError,
    InvalidCredentialsError,
    UserNotFoundError,
    PermissionDeniedError
)

__all__ = [
    # 基础类
    "AuthComponent",
    "UserInfo",
    "AuthStatus",
    
    # 异常类
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "TokenError",
    "TokenExpiredError",
    "InvalidCredentialsError",
    "UserNotFoundError",
    "PermissionDeniedError"
] 