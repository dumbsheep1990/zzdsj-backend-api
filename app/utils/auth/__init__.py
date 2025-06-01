"""
认证授权模块
提供JWT处理、用户认证、权限验证等认证授权功能的统一接口
"""

from .jwt_handler import *

__all__ = [
    # JWT处理
    "JWTHandler",
    "create_access_token",
    "verify_token",
    "decode_token",
    "get_current_user",
    
    # 认证功能
    "authenticate_user",
    "check_permissions",
    "require_auth"
]
