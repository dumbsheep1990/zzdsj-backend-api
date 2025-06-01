"""
监控模块异常定义
"""


class MonitoringError(Exception):
    """
    监控模块基础异常类
    """
    
    def __init__(self, message: str, code: str = None, component: str = None):
        """
        初始化异常
        
        参数:
            message: 错误消息
            code: 错误代码
            component: 组件名称
        """
        super().__init__(message)
        self.message = message
        self.code = code or "MONITORING_ERROR"
        self.component = component


class MetricsCollectionError(MonitoringError):
    """
    指标收集异常
    """
    
    def __init__(self, message: str = "Metrics collection failed", metric_name: str = None, **kwargs):
        """
        初始化异常
        
        参数:
            message: 错误消息
            metric_name: 指标名称
        """
        super().__init__(message, "METRICS_COLLECTION_ERROR", **kwargs)
        self.metric_name = metric_name


class HealthCheckError(MonitoringError):
    """
    健康检查异常
    """
    
    def __init__(self, message: str = "Health check failed", service_name: str = None, **kwargs):
        """
        初始化异常
        
        参数:
            message: 错误消息
            service_name: 服务名称
        """
        super().__init__(message, "HEALTH_CHECK_ERROR", **kwargs)
        self.service_name = service_name 