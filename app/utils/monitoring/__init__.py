"""
监控指标模块
提供系统监控、健康检查、指标收集等监控相关功能的统一接口

重构后的模块结构:
- core: 核心组件和指标框架
- token_metrics: Token使用指标
- health_monitor: 健康监控
"""

# 导入新的重构后的组件
from .core import (
    MonitoringComponent, 
    MetricsCollector, 
    Metric, 
    MetricType,
    MonitoringError, 
    MetricsCollectionError, 
    HealthCheckError
)

# 为了保持向后兼容，也从旧的文件导入（如果需要）
try:
    # 如果旧文件还存在，提供别名以保持兼容性
    from .token_metrics import TokenMetrics, get_token_metrics, track_token_usage, get_usage_statistics
    from .health_monitor import HealthMonitor, check_service_health, get_health_status, register_health_check
    
    # 保持旧的导入路径可用
    __all__ = [
        # 新的重构后接口
        "MonitoringComponent",
        "MetricsCollector",
        "Metric",
        "MetricType", 
        "MonitoringError",
        "MetricsCollectionError",
        "HealthCheckError",
        
        # 向后兼容的旧接口
        "TokenMetrics",
        "get_token_metrics",
        "track_token_usage", 
        "get_usage_statistics",
        "HealthMonitor",
        "check_service_health",
        "get_health_status",
        "register_health_check"
    ]
    
except ImportError:
    # 如果旧文件不存在，只导出新接口
    __all__ = [
        # 新的重构后接口
        "MonitoringComponent",
        "MetricsCollector", 
        "Metric",
        "MetricType",
        "MonitoringError",
        "MetricsCollectionError",
        "HealthCheckError"
    ]
