"""
API共享异常处理系统
提供双层API架构的统一异常定义和处理机制
"""

from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# ================================
# 基础异常类
# ================================

class APIBaseException(Exception, ABC):
    """API基础异常抽象类"""
    
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message": self.message,
            "code": self.code,
            "status_code": self.status_code,
            "details": self.details
        }
    
    @abstractmethod
    def get_log_level(self) -> str:
        """获取日志级别"""
        pass


# ================================
# 对外API异常类
# ================================

class ExternalAPIException(APIBaseException):
    """对外API异常基类"""
    
    def get_log_level(self) -> str:
        """对外API异常一般记录为warning级别"""
        return "warning"


class InvalidRequestException(ExternalAPIException):
    """无效请求异常"""
    
    def __init__(self, message: str = "请求参数无效", field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if field:
            message = f"{message}: {field}"
        super().__init__(
            message=message,
            code="invalid_request",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )
        self.field = field


class AuthenticationFailedException(ExternalAPIException):
    """认证失败异常"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="authentication_failed",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class InsufficientPermissionException(ExternalAPIException):
    """权限不足异常"""
    
    def __init__(self, message: str = "权限不足", required_permission: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if required_permission:
            message = f"{message}: 需要{required_permission}权限"
        super().__init__(
            message=message,
            code="insufficient_permission",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )
        self.required_permission = required_permission


class ResourceNotFoundError(ExternalAPIException):
    """资源不存在异常"""
    
    def __init__(self, resource: str, identifier: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource}不存在"
        if identifier:
            message = f"{resource} '{identifier}' 不存在"
        
        super().__init__(
            message=message,
            code="resource_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )
        self.resource = resource
        self.identifier = identifier


class RateLimitExceededException(ExternalAPIException):
    """频率限制异常"""
    
    def __init__(self, message: str = "请求频率过高", retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if not details:
            details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )
        self.retry_after = retry_after


class ServiceUnavailableError(ExternalAPIException):
    """服务不可用异常"""
    
    def __init__(self, service: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_message = message or f"{service}服务暂时不可用"
        super().__init__(
            message=error_message,
            code="service_unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )
        self.service = service


# ================================
# 内部API异常类
# ================================

class InternalAPIException(APIBaseException):
    """内部API异常基类"""
    
    def get_log_level(self) -> str:
        """内部API异常一般记录为error级别"""
        return "error"


class ConfigurationError(InternalAPIException):
    """配置错误异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if config_key:
            message = f"配置错误 [{config_key}]: {message}"
        super().__init__(
            message=message,
            code="configuration_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )
        self.config_key = config_key


class SystemMaintenanceError(InternalAPIException):
    """系统维护异常"""
    
    def __init__(self, message: str = "系统正在维护", maintenance_window: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if maintenance_window:
            message = f"{message}，预计维护时间: {maintenance_window}"
        super().__init__(
            message=message,
            code="system_maintenance",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )
        self.maintenance_window = maintenance_window


class DatabaseError(InternalAPIException):
    """数据库异常"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if operation:
            message = f"数据库操作失败 [{operation}]: {message}"
        super().__init__(
            message=message,
            code="database_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )
        self.operation = operation


class ExternalServiceError(InternalAPIException):
    """外部服务异常"""
    
    def __init__(self, service: str, message: str, status_code: int = status.HTTP_502_BAD_GATEWAY, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service}服务异常: {message}",
            code="external_service_error",
            status_code=status_code,
            details=details
        )
        self.service = service


# ================================
# 业务异常类
# ================================

class BusinessLogicError(APIBaseException):
    """业务逻辑异常"""
    
    def __init__(self, message: str, business_code: str = "business_error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=business_code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )
    
    def get_log_level(self) -> str:
        return "warning"


class ValidationError(BusinessLogicError):
    """数据验证异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, validation_errors: Optional[List[Dict]] = None):
        details = {}
        if field:
            details["field"] = field
        if validation_errors:
            details["validation_errors"] = validation_errors
        
        super().__init__(
            message=message,
            business_code="validation_error",
            details=details
        )
        self.field = field
        self.validation_errors = validation_errors


class ConflictError(BusinessLogicError):
    """资源冲突异常"""
    
    def __init__(self, message: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            business_code="conflict",
            details=details
        )
        self.resource = resource
        self.status_code = status.HTTP_409_CONFLICT


# ================================
# 特定业务领域异常
# ================================

class AssistantError(BusinessLogicError):
    """助手相关异常"""
    
    def __init__(self, message: str, assistant_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            business_code="assistant_error",
            details=details
        )
        self.assistant_id = assistant_id


class KnowledgeBaseError(BusinessLogicError):
    """知识库相关异常"""
    
    def __init__(self, message: str, knowledge_base_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            business_code="knowledge_base_error",
            details=details
        )
        self.knowledge_base_id = knowledge_base_id


class ChatError(BusinessLogicError):
    """聊天相关异常"""
    
    def __init__(self, message: str, chat_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            business_code="chat_error",
            details=details
        )
        self.chat_id = chat_id


class ModelProviderError(BusinessLogicError):
    """模型提供商异常"""
    
    def __init__(self, message: str, provider: Optional[str] = None, model: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if provider and model:
            message = f"模型提供商 {provider} 的模型 {model}: {message}"
        elif provider:
            message = f"模型提供商 {provider}: {message}"
        
        super().__init__(
            message=message,
            business_code="model_provider_error",
            details=details
        )
        self.provider = provider
        self.model = model


class ToolExecutionError(BusinessLogicError):
    """工具执行异常"""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, execution_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if tool_name:
            message = f"工具 {tool_name} 执行失败: {message}"
        
        super().__init__(
            message=message,
            business_code="tool_execution_error",
            details=details
        )
        self.tool_name = tool_name
        self.execution_id = execution_id


# ================================
# 异常处理器类
# ================================

class ExceptionHandler:
    """统一异常处理器"""
    
    @staticmethod
    def get_api_type_from_request(request: Request) -> str:
        """从请求路径判断API类型"""
        path = request.url.path
        if path.startswith("/api/external/"):
            return "external"
        elif path.startswith("/api/internal/"):
            return "internal"
        elif path.startswith("/api/v1/"):
            return "external"  # v1被认为是对外API
        else:
            return "external"  # 默认为对外API
    
    @staticmethod
    async def handle_api_exception(request: Request, exc: APIBaseException) -> JSONResponse:
        """处理自定义API异常"""
        api_type = ExceptionHandler.get_api_type_from_request(request)
        request_id = getattr(request.state, "request_id", None)
        
        # 记录日志
        log_level = exc.get_log_level()
        log_message = f"API异常 [{api_type}]: {exc.code} - {exc.message}"
        log_extra = {
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "details": exc.details
        }
        
        if log_level == "error":
            logger.error(log_message, extra=log_extra, exc_info=True)
        elif log_level == "warning":
            logger.warning(log_message, extra=log_extra)
        else:
            logger.info(log_message, extra=log_extra)
        
        # 根据API类型选择响应格式
        from .responses import handle_exception_response
        return handle_exception_response(
            exception=exc,
            request_id=request_id,
            api_type=api_type,
            include_debug=(api_type == "internal")
        )
    
    @staticmethod
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        """处理FastAPI HTTPException"""
        api_type = ExceptionHandler.get_api_type_from_request(request)
        request_id = getattr(request.state, "request_id", None)
        
        logger.warning(
            f"HTTP异常 [{api_type}]: {exc.status_code} - {exc.detail}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
        
        from .responses import handle_exception_response
        return handle_exception_response(
            exception=exc,
            request_id=request_id,
            api_type=api_type,
            include_debug=(api_type == "internal")
        )
    
    @staticmethod
    async def handle_starlette_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """处理Starlette HTTPException"""
        api_type = ExceptionHandler.get_api_type_from_request(request)
        request_id = getattr(request.state, "request_id", None)
        
        logger.warning(
            f"Starlette HTTP异常 [{api_type}]: {exc.status_code} - {exc.detail}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code
            }
        )
        
        from .responses import handle_exception_response
        return handle_exception_response(
            exception=exc,
            request_id=request_id,
            api_type=api_type,
            include_debug=(api_type == "internal")
        )
    
    @staticmethod
    async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
        """处理请求验证异常"""
        api_type = ExceptionHandler.get_api_type_from_request(request)
        request_id = getattr(request.state, "request_id", None)
        
        # 格式化验证错误
        validation_errors = []
        for error in exc.errors():
            field_path = " -> ".join(str(x) for x in error["loc"])
            validation_errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })
        
        logger.warning(
            f"请求验证异常 [{api_type}]: {len(validation_errors)} 个错误",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "errors": validation_errors
            }
        )
        
        # 创建验证异常对象
        validation_error = ValidationError(
            message="请求数据验证失败",
            validation_errors=validation_errors
        )
        
        from .responses import handle_exception_response
        return handle_exception_response(
            exception=validation_error,
            request_id=request_id,
            api_type=api_type,
            include_debug=(api_type == "internal")
        )
    
    @staticmethod
    async def handle_general_exception(request: Request, exc: Exception) -> JSONResponse:
        """处理通用异常"""
        api_type = ExceptionHandler.get_api_type_from_request(request)
        request_id = getattr(request.state, "request_id", None)
        
        logger.error(
            f"未处理异常 [{api_type}]: {type(exc).__name__} - {str(exc)}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__
            },
            exc_info=True
        )
        
        # 根据API类型创建不同的内部错误
        if api_type == "external":
            # 对外API不暴露内部错误详情
            internal_error = ExternalAPIException(
                message="服务器内部错误",
                code="internal_server_error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        else:
            # 内部API可以提供更多错误信息
            internal_error = InternalAPIException(
                message=f"内部服务器错误: {str(exc)}",
                code="internal_server_error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details={
                    "exception_type": type(exc).__name__,
                    "module": getattr(exc, '__module__', 'unknown')
                }
            )
        
        from .responses import handle_exception_response
        return handle_exception_response(
            exception=internal_error,
            request_id=request_id,
            api_type=api_type,
            include_debug=(api_type == "internal")
        )


# ================================
# 异常装饰器
# ================================

def handle_exceptions(
    log_errors: bool = True,
    convert_to_api_exception: bool = True
):
    """
    异常处理装饰器
    
    Args:
        log_errors: 是否记录错误日志
        convert_to_api_exception: 是否转换为API异常
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except APIBaseException:
                # 重新抛出API异常
                raise
            except Exception as e:
                if log_errors:
                    logger.error(f"函数 {func.__name__} 执行异常: {str(e)}", exc_info=True)
                
                if convert_to_api_exception:
                    # 转换为API异常
                    raise InternalAPIException(
                        message=f"操作执行失败: {str(e)}",
                        code="execution_error",
                        details={
                            "function": func.__name__,
                            "original_error": str(e),
                            "error_type": type(e).__name__
                        }
                    )
                else:
                    # 重新抛出原异常
                    raise
        
        return wrapper
    return decorator


def require_resource(resource_name: str):
    """
    资源存在检查装饰器
    
    Args:
        resource_name: 资源名称
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if result is None:
                raise ResourceNotFoundError(resource_name)
            return result
        
        return wrapper
    return decorator


def validate_business_rules(*rules):
    """
    业务规则验证装饰器
    
    Args:
        rules: 业务规则函数列表
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 执行业务规则验证
            for rule in rules:
                if callable(rule):
                    try:
                        if not await rule(*args, **kwargs):
                            raise BusinessLogicError("业务规则验证失败")
                    except APIBaseException:
                        raise
                    except Exception as e:
                        raise BusinessLogicError(f"业务规则验证异常: {str(e)}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ================================
# 工具函数
# ================================

def raise_not_found(resource: str, identifier: Optional[str] = None):
    """抛出资源不存在异常的快捷函数"""
    raise ResourceNotFoundError(resource, identifier)


def raise_conflict(message: str, resource: Optional[str] = None):
    """抛出资源冲突异常的快捷函数"""
    raise ConflictError(message, resource)


def raise_validation_error(message: str, field: Optional[str] = None):
    """抛出验证错误异常的快捷函数"""
    raise ValidationError(message, field)


def raise_business_error(message: str, code: str = "business_error"):
    """抛出业务逻辑错误异常的快捷函数"""
    raise BusinessLogicError(message, code)


def raise_authentication_failed(message: str = "认证失败"):
    """抛出认证失败异常的快捷函数"""
    raise AuthenticationFailedException(message)


def raise_insufficient_permission(message: str = "权限不足", required_permission: Optional[str] = None):
    """抛出权限不足异常的快捷函数"""
    raise InsufficientPermissionException(message, required_permission)


def raise_rate_limit_exceeded(message: str = "请求频率过高", retry_after: Optional[int] = None):
    """抛出频率限制异常的快捷函数"""
    raise RateLimitExceededException(message, retry_after)


# ================================
# 异常注册函数
# ================================

def register_exception_handlers(app):
    """
    注册所有异常处理器到FastAPI应用
    
    Args:
        app: FastAPI应用实例
    """
    # 自定义API异常
    app.add_exception_handler(APIBaseException, ExceptionHandler.handle_api_exception)
    
    # FastAPI HTTP异常
    app.add_exception_handler(HTTPException, ExceptionHandler.handle_http_exception)
    
    # Starlette HTTP异常
    app.add_exception_handler(StarletteHTTPException, ExceptionHandler.handle_starlette_http_exception)
    
    # 请求验证异常
    app.add_exception_handler(RequestValidationError, ExceptionHandler.handle_validation_exception)
    
    # 通用异常（最后的fallback）
    app.add_exception_handler(Exception, ExceptionHandler.handle_general_exception) 