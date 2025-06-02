"""
Services模块异常定义
提供服务管理相关的异常类
"""


class ServiceError(Exception):
    """服务管理基础异常"""
    
    def __init__(self, message: str, service_name: str = "", error_code: str = ""):
        self.message = message
        self.service_name = service_name
        self.error_code = error_code
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "error": "ServiceError",
            "message": self.message,
            "service_name": self.service_name,
            "error_code": self.error_code
        }


class ServiceNotFoundError(ServiceError):
    """服务未找到异常"""
    
    def __init__(self, service_name: str):
        super().__init__(
            message=f"服务未找到: {service_name}",
            service_name=service_name,
            error_code="SERVICE_NOT_FOUND"
        )


class ServiceInitializationError(ServiceError):
    """服务初始化异常"""
    
    def __init__(self, service_name: str, details: str = ""):
        message = f"服务初始化失败: {service_name}"
        if details:
            message += f" - {details}"
        super().__init__(
            message=message,
            service_name=service_name,
            error_code="SERVICE_INIT_FAILED"
        )


class ServiceStartupError(ServiceError):
    """服务启动异常"""
    
    def __init__(self, service_name: str, details: str = ""):
        message = f"服务启动失败: {service_name}"
        if details:
            message += f" - {details}"
        super().__init__(
            message=message,
            service_name=service_name,
            error_code="SERVICE_STARTUP_FAILED"
        )


class ServiceStopError(ServiceError):
    """服务停止异常"""
    
    def __init__(self, service_name: str, details: str = ""):
        message = f"服务停止失败: {service_name}"
        if details:
            message += f" - {details}"
        super().__init__(
            message=message,
            service_name=service_name,
            error_code="SERVICE_STOP_FAILED"
        )


class ServiceDiscoveryError(ServiceError):
    """服务发现异常"""
    
    def __init__(self, message: str, details: str = ""):
        full_message = f"服务发现失败: {message}"
        if details:
            full_message += f" - {details}"
        super().__init__(
            message=full_message,
            error_code="SERVICE_DISCOVERY_FAILED"
        )


class ServiceRegistrationError(ServiceError):
    """服务注册异常"""
    
    def __init__(self, service_name: str, details: str = ""):
        message = f"服务注册失败: {service_name}"
        if details:
            message += f" - {details}"
        super().__init__(
            message=message,
            service_name=service_name,
            error_code="SERVICE_REGISTRATION_FAILED"
        )


class ServiceHealthCheckError(ServiceError):
    """服务健康检查异常"""
    
    def __init__(self, service_name: str, details: str = ""):
        message = f"服务健康检查失败: {service_name}"
        if details:
            message += f" - {details}"
        super().__init__(
            message=message,
            service_name=service_name,
            error_code="SERVICE_HEALTH_CHECK_FAILED"
        ) 