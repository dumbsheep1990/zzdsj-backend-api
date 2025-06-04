"""
助手模块自定义异常
"""


class BaseAssistantError(Exception):
    """助手模块基础异常"""
    def __init__(self, message: str = "助手模块错误", code: str = "ASSISTANT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class AssistantNotFoundError(BaseAssistantError):
    """助手未找到"""
    def __init__(self, assistant_id: int):
        super().__init__(
            message=f"助手 {assistant_id} 不存在",
            code="ASSISTANT_NOT_FOUND"
        )


class ConversationNotFoundError(BaseAssistantError):
    """对话未找到"""
    def __init__(self, conversation_id: int):
        super().__init__(
            message=f"对话 {conversation_id} 不存在",
            code="CONVERSATION_NOT_FOUND"
        )


class PermissionDeniedError(BaseAssistantError):
    """权限不足"""
    def __init__(self, resource: str = "资源"):
        super().__init__(
            message=f"无权访问该{resource}",
            code="PERMISSION_DENIED"
        )


class ValidationError(BaseAssistantError):
    """数据验证错误"""
    def __init__(self, field: str, reason: str):
        super().__init__(
            message=f"字段 {field} 验证失败: {reason}",
            code="VALIDATION_ERROR"
        )


class QuotaExceededError(BaseAssistantError):
    """配额超限"""
    def __init__(self, resource: str, limit: int):
        super().__init__(
            message=f"{resource}数量已达上限 {limit}",
            code="QUOTA_EXCEEDED"
        )


class ExternalServiceError(BaseAssistantError):
    """外部服务错误"""
    def __init__(self, service: str, reason: str):
        super().__init__(
            message=f"外部服务 {service} 错误: {reason}",
            code="EXTERNAL_SERVICE_ERROR"
        )