"""
JWT子模块
提供JWT令牌处理功能
"""

# 从原有文件导入，保持兼容性
from .handler import *

__all__ = [
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
] 