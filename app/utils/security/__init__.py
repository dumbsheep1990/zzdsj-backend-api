"""
安全工具模块
提供限流器、敏感词过滤等安全相关功能的统一接口

重构后的模块结构:
- core: 核心组件和异常定义
- rate_limiting: 速率限制功能  
- content_filtering: 内容过滤功能
"""

# 导入新的重构后的组件
from .core import SecurityComponent, SecurityError, RateLimitExceeded, ContentFilterError
from .rate_limiting import RateLimiter, create_rate_limiter, check_rate_limit
from .content_filtering import (
    SensitiveWordFilter, 
    get_sensitive_word_filter,
    filter_sensitive_words,
    detect_sensitive_content,
    load_sensitive_words
)

# 为了保持向后兼容，也从旧的文件导入（如果需要）
try:
    # 如果旧文件还存在，提供别名以保持兼容性
    from .rate_limiter import RateLimiter as OldRateLimiter
    from .sensitive_filter import SensitiveWordFilter as OldSensitiveWordFilter
    from .sensitive_filter import get_sensitive_word_filter as old_get_sensitive_word_filter
    
    # 保持旧的导入路径可用
    __all__ = [
        # 新的重构后接口
        "SecurityComponent",
        "SecurityError", 
        "RateLimitExceeded",
        "ContentFilterError",
        
        # 限流器
        "RateLimiter",
        "create_rate_limiter",
        "check_rate_limit",
        
        # 敏感词过滤
        "SensitiveWordFilter", 
        "get_sensitive_word_filter",
        "filter_sensitive_words",
        "detect_sensitive_content",
        "load_sensitive_words",
        
        # 向后兼容的旧接口
        "OldRateLimiter",
        "OldSensitiveWordFilter",
        "old_get_sensitive_word_filter"
    ]
    
except ImportError:
    # 如果旧文件不存在，只导出新接口
    __all__ = [
        # 新的重构后接口
        "SecurityComponent",
        "SecurityError", 
        "RateLimitExceeded",
        "ContentFilterError",
        
        # 限流器
        "RateLimiter",
        "create_rate_limiter",
        "check_rate_limit",
        
        # 敏感词过滤
        "SensitiveWordFilter", 
        "get_sensitive_word_filter",
        "filter_sensitive_words",
        "detect_sensitive_content",
        "load_sensitive_words"
    ]
