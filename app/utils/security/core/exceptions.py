"""
安全模块异常定义
"""


class SecurityError(Exception):
    """
    安全模块基础异常类
    """
    
    def __init__(self, message: str, code: str = None):
        """
        初始化异常
        
        参数:
            message: 错误消息
            code: 错误代码
        """
        super().__init__(message)
        self.message = message
        self.code = code or "SECURITY_ERROR"


class RateLimitExceeded(SecurityError):
    """
    速率限制超出异常
    """
    
    def __init__(self, message: str = "Rate limit exceeded", remaining: int = 0, reset_time: float = 0):
        """
        初始化异常
        
        参数:
            message: 错误消息
            remaining: 剩余请求数
            reset_time: 重置时间
        """
        super().__init__(message, "RATE_LIMIT_EXCEEDED")
        self.remaining = remaining
        self.reset_time = reset_time


class ContentFilterError(SecurityError):
    """
    内容过滤异常
    """
    
    def __init__(self, message: str = "Content filtered", detected_words: list = None):
        """
        初始化异常
        
        参数:
            message: 错误消息
            detected_words: 检测到的敏感词列表
        """
        super().__init__(message, "CONTENT_FILTERED")
        self.detected_words = detected_words or [] 