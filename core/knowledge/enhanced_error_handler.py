"""
增强的错误处理机制
提供智能降级、熔断器、重试策略和错误恢复功能，确保检索系统的高可用性
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import functools
import traceback
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(str, Enum):
    """错误严重级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    service_name: str
    operation_name: str
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    resolution_attempted: bool = False
    resolved: bool = False


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: int = 60  # 恢复超时（秒）
    half_open_max_calls: int = 3  # 半开状态最大调用次数
    success_threshold: int = 2  # 半开状态成功阈值


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 60.0  # 最大延迟
    exponential_base: float = 2.0  # 指数退避基数
    jitter: bool = True  # 是否添加抖动


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self.half_open_successes = 0
        
    def can_execute(self) -> bool:
        """判断是否可以执行操作"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # 检查是否可以转为半开状态
            if (self.last_failure_time and 
                datetime.now() - self.last_failure_time > timedelta(seconds=self.config.recovery_timeout)):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                self.half_open_successes = 0
                logger.info(f"熔断器 {self.name} 转为半开状态")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def record_success(self):
        """记录成功执行"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"熔断器 {self.name} 恢复到正常状态")
        
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """记录失败执行"""
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"熔断器 {self.name} 开启，失败次数: {self.failure_count}")
        
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"熔断器 {self.name} 重新开启")
    
    def record_call(self):
        """记录调用"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1


class EnhancedErrorHandler:
    """增强的错误处理器"""
    
    def __init__(self):
        """初始化错误处理器"""
        self._error_history: List[ErrorRecord] = []
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._fallback_strategies: Dict[str, Callable] = {}
        self._error_handlers: Dict[str, Callable] = {}
        self._max_history_size = 1000
        self._cleanup_interval = 3600  # 清理间隔（秒）
        self._last_cleanup = datetime.now()
        
    def register_circuit_breaker(
        self, 
        service_name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ):
        """注册熔断器"""
        if config is None:
            config = CircuitBreakerConfig()
        
        self._circuit_breakers[service_name] = CircuitBreaker(service_name, config)
        logger.info(f"已注册熔断器: {service_name}")
    
    def register_fallback_strategy(self, service_name: str, fallback_func: Callable):
        """注册降级策略"""
        self._fallback_strategies[service_name] = fallback_func
        logger.info(f"已注册降级策略: {service_name}")
    
    def register_error_handler(self, error_type: str, handler_func: Callable):
        """注册错误处理器"""
        self._error_handlers[error_type] = handler_func
        logger.info(f"已注册错误处理器: {error_type}")
    
    async def handle_error(
        self,
        error: Exception,
        service_name: str,
        operation_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorRecord:
        """
        处理错误
        
        Args:
            error: 异常对象
            service_name: 服务名称
            operation_name: 操作名称
            context: 上下文信息
            
        Returns:
            错误记录
        """
        try:
            # 创建错误记录
            error_record = ErrorRecord(
                timestamp=datetime.now(),
                error_type=type(error).__name__,
                error_message=str(error),
                severity=self._determine_severity(error),
                service_name=service_name,
                operation_name=operation_name,
                context=context or {},
                stack_trace=traceback.format_exc()
            )
            
            # 记录错误
            self._error_history.append(error_record)
            logger.error(f"错误处理: {service_name}.{operation_name} - {error_record.error_message}")
            
            # 更新熔断器状态
            if service_name in self._circuit_breakers:
                self._circuit_breakers[service_name].record_failure()
            
            # 尝试自动恢复
            await self._attempt_recovery(error_record)
            
            return error_record
            
        except Exception as e:
            logger.error(f"错误处理器本身发生异常: {str(e)}")
            # 返回最基本的错误记录
            return ErrorRecord(
                timestamp=datetime.now(),
                error_type="ErrorHandlerException",
                error_message=str(e),
                severity=ErrorSeverity.CRITICAL,
                service_name="error_handler",
                operation_name="handle_error"
            )
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """确定错误严重级别"""
        error_type = type(error).__name__
        
        # 关键错误
        critical_errors = [
            "SystemExit", "KeyboardInterrupt", "MemoryError",
            "ConnectionError", "DatabaseError"
        ]
        if error_type in critical_errors:
            return ErrorSeverity.CRITICAL
        
        # 高级错误
        high_errors = [
            "TimeoutError", "PermissionError", "AuthenticationError",
            "ValidationError"
        ]
        if error_type in high_errors:
            return ErrorSeverity.HIGH
        
        # 中级错误
        medium_errors = [
            "ValueError", "TypeError", "AttributeError",
            "KeyError", "IndexError"
        ]
        if error_type in medium_errors:
            return ErrorSeverity.MEDIUM
        
        # 默认为低级错误
        return ErrorSeverity.LOW
    
    async def _attempt_recovery(self, error_record: ErrorRecord):
        """尝试自动恢复"""
        try:
            error_record.resolution_attempted = True
            
            # 查找特定错误处理器
            error_type = error_record.error_type
            if error_type in self._error_handlers:
                handler = self._error_handlers[error_type]
                result = await handler(error_record)
                if result:
                    error_record.resolved = True
                    logger.info(f"错误自动恢复成功: {error_record.error_type}")
            
        except Exception as e:
            logger.error(f"自动恢复失败: {str(e)}")
    
    @asynccontextmanager
    async def circuit_breaker_context(self, service_name: str):
        """熔断器上下文管理器"""
        circuit_breaker = self._circuit_breakers.get(service_name)
        
        if not circuit_breaker:
            # 如果没有熔断器，直接执行
            yield
            return
        
        if not circuit_breaker.can_execute():
            # 熔断器开启，执行降级策略
            if service_name in self._fallback_strategies:
                fallback = self._fallback_strategies[service_name]
                yield fallback
            else:
                raise Exception(f"服务 {service_name} 熔断且无降级策略")
            return
        
        # 记录调用
        circuit_breaker.record_call()
        
        try:
            yield
            # 执行成功
            circuit_breaker.record_success()
            
        except Exception as e:
            # 执行失败
            circuit_breaker.record_failure()
            raise
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        try:
            if not self._error_history:
                return {
                    "total_errors": 0,
                    "by_severity": {},
                    "by_service": {},
                    "by_type": {},
                    "circuit_breakers": {}
                }
            
            total_errors = len(self._error_history)
            
            # 按严重级别统计
            by_severity = {}
            for record in self._error_history:
                severity = record.severity.value
                by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # 按服务统计
            by_service = {}
            for record in self._error_history:
                service = record.service_name
                by_service[service] = by_service.get(service, 0) + 1
            
            # 按错误类型统计
            by_type = {}
            for record in self._error_history:
                error_type = record.error_type
                by_type[error_type] = by_type.get(error_type, 0) + 1
            
            return {
                "total_errors": total_errors,
                "by_severity": by_severity,
                "by_service": by_service,
                "by_type": by_type,
                "circuit_breakers": {
                    name: {
                        "state": cb.state.value,
                        "failure_count": cb.failure_count
                    }
                    for name, cb in self._circuit_breakers.items()
                }
            }
            
        except Exception as e:
            logger.error(f"获取错误统计失败: {str(e)}")
            return {"error": str(e)}


def with_error_handling(
    service_name: str,
    operation_name: str,
    error_handler: Optional[EnhancedErrorHandler] = None
):
    """错误处理装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            handler = error_handler or get_error_handler()
            
            try:
                # 使用熔断器上下文
                async with handler.circuit_breaker_context(service_name):
                    result = await func(*args, **kwargs)
                    return result
                    
            except Exception as e:
                # 处理错误
                await handler.handle_error(e, service_name, operation_name)
                
                # 尝试降级策略
                if service_name in handler._fallback_strategies:
                    fallback = handler._fallback_strategies[service_name]
                    return await fallback(*args, **kwargs)
                
                # 重新抛出异常
                raise
        
        return wrapper
    return decorator


def with_retry(retry_config: Optional[RetryConfig] = None):
    """重试装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            config = retry_config or RetryConfig()
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # 最后一次尝试，抛出异常
                        break
                    
                    # 计算延迟时间
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # 添加抖动
                    if config.jitter:
                        import random
                        delay *= (0.5 + 0.5 * random.random())
                    
                    logger.info(f"重试第 {attempt + 1} 次，延迟 {delay:.2f} 秒")
                    await asyncio.sleep(delay)
            
            # 抛出最后的异常
            raise last_exception
        
        return wrapper
    return decorator


# 全局错误处理器实例
_error_handler: Optional[EnhancedErrorHandler] = None


def get_error_handler() -> EnhancedErrorHandler:
    """获取错误处理器实例"""
    global _error_handler
    if _error_handler is None:
        _error_handler = EnhancedErrorHandler()
    return _error_handler


def setup_default_error_handling():
    """设置默认的错误处理配置"""
    handler = get_error_handler()
    
    # 注册常用服务的熔断器
    services = ["elasticsearch", "milvus", "pgvector", "redis"]
    for service in services:
        handler.register_circuit_breaker(service)
    
    # 注册默认错误处理器
    async def timeout_handler(error_record: ErrorRecord) -> bool:
        """超时错误处理器"""
        if "timeout" in error_record.error_message.lower():
            logger.info(f"处理超时错误: {error_record.service_name}")
            return True
        return False
    
    handler.register_error_handler("TimeoutError", timeout_handler)
    
    logger.info("默认错误处理配置已设置") 