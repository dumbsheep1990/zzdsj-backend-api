"""
安全模块核心组件
提供抽象基类和异常定义
"""

from .base import SecurityComponent
from .exceptions import SecurityError, RateLimitExceeded, ContentFilterError

__all__ = [
    "SecurityComponent",
    "SecurityError", 
    "RateLimitExceeded",
    "ContentFilterError"
] 