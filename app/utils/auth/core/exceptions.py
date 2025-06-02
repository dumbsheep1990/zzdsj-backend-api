"""
Auth模块异常定义
提供认证授权相关的异常类
"""


class AuthError(Exception):
    """认证授权基础异常"""
    
    def __init__(self, message: str, error_code: str = "", details: str = ""):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "error": "AuthError",
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class AuthenticationError(AuthError):
    """认证失败异常"""
    
    def __init__(self, message: str = "认证失败", details: str = ""):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            details=details
        )


class AuthorizationError(AuthError):
    """授权失败异常"""
    
    def __init__(self, message: str = "权限不足", resource: str = "", action: str = ""):
        details = f"资源: {resource}, 动作: {action}" if resource and action else ""
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            details=details
        )


class TokenError(AuthError):
    """令牌异常"""
    
    def __init__(self, message: str = "令牌无效", details: str = ""):
        super().__init__(
            message=message,
            error_code="TOKEN_ERROR",
            details=details
        )


class TokenExpiredError(TokenError):
    """令牌过期异常"""
    
    def __init__(self, message: str = "令牌已过期", details: str = ""):
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            details=details
        )


class InvalidCredentialsError(AuthenticationError):
    """无效凭据异常"""
    
    def __init__(self, message: str = "用户名或密码错误", details: str = ""):
        super().__init__(
            message=message,
            details=details
        )


class UserNotFoundError(AuthenticationError):
    """用户未找到异常"""
    
    def __init__(self, username: str):
        super().__init__(
            message=f"用户不存在: {username}",
            details=f"用户名: {username}"
        )


class PermissionDeniedError(AuthorizationError):
    """权限拒绝异常"""
    
    def __init__(self, permission: str, details: str = ""):
        super().__init__(
            message=f"权限被拒绝: {permission}",
            details=details
        ) 