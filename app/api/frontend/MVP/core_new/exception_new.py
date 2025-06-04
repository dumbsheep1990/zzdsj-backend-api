"""
自定义异常类，用于服务层的错误处理
"""


class BaseServiceError(Exception):
    """服务层基础异常类"""
    def __init__(self, message: str = "服务错误"):
        self.message = message
        super().__init__(self.message)


class NotFoundError(BaseServiceError):
    """资源未找到异常"""
    def __init__(self, message: str = "资源未找到"):
        super().__init__(message)


class PermissionError(BaseServiceError):
    """权限不足异常"""
    def __init__(self, message: str = "权限不足"):
        super().__init__(message)


class ValidationError(BaseServiceError):
    """数据验证异常"""
    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message)


class ConflictError(BaseServiceError):
    """资源冲突异常"""
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message)


class ExternalServiceError(BaseServiceError):
    """外部服务异常"""
    def __init__(self, message: str = "外部服务错误"):
        super().__init__(message)# 助手模块优化指南