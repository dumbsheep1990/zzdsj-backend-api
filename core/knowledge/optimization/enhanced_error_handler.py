"""
增强错误处理器
提供熔断器模式、智能回退和自动恢复机制
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, Any, List, Optional, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import functools
import random

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"           # 关闭状态（正常）
    OPEN = "open"              # 开启状态（熔断）
    HALF_OPEN = "half_open"    # 半开状态（测试恢复）


class FallbackStrategy(str, Enum):
    """回退策略"""
    IMMEDIATE = "immediate"         # 立即回退
    RETRY_THEN_FALLBACK = "retry_then_fallback"  # 重试后回退
    GRACEFUL_DEGRADATION = "graceful_degradation"  # 优雅降级
    FAIL_FAST = "fail_fast"        # 快速失败


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"           # 轻微错误
    MEDIUM = "medium"     # 中等错误
    HIGH = "high"         # 严重错误
    CRITICAL = "critical" # 致命错误


@dataclass
class ErrorPattern:
    """错误模式"""
    error_type: str
    pattern: str
    severity: ErrorSeverity
    action: str
    frequency_threshold: int = 5
    time_window: int = 300  # 5分钟


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5          # 失败阈值
    recovery_timeout: int = 60          # 恢复超时（秒）
    success_threshold: int = 3          # 半开状态成功阈值
    timeout: int = 30                   # 请求超时
    monitor_window: int = 300           # 监控窗口（秒）
    
    # 回退配置
    fallback_strategy: FallbackStrategy = FallbackStrategy.GRACEFUL_DEGRADATION
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class ErrorStatistics:
    """错误统计"""
    total_requests: int = 0
    failed_requests: int = 0
    success_requests: int = 0
    avg_response_time: float = 0.0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    failure_rate: float = 0.0
    
    # 错误类型统计
    error_types: Dict[str, int] = field(default_factory=dict)
    
    def update_success(self, response_time: float) -> None:
        """更新成功统计"""
        self.total_requests += 1
        self.success_requests += 1
        self.last_success_time = time.time()
        
        # 更新平均响应时间
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time + response_time) / 2
        
        self._update_failure_rate()
    
    def update_failure(self, error_type: str) -> None:
        """更新失败统计"""
        self.total_requests += 1
        self.failed_requests += 1
        self.last_failure_time = time.time()
        
        # 更新错误类型统计
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
        
        self._update_failure_rate()
    
    def _update_failure_rate(self) -> None:
        """更新失败率"""
        if self.total_requests > 0:
            self.failure_rate = self.failed_requests / self.total_requests


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """初始化熔断器"""
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.stats = ErrorStatistics()
        
        # 状态追踪
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.next_attempt_time = 0.0
        
        # 最近请求记录
        self.recent_requests: deque = deque(maxlen=100)
        
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器调用函数"""
        async with self._lock:
            # 检查熔断器状态
            await self._check_state()
            
            if self.state == CircuitBreakerState.OPEN:
                raise CircuitBreakerOpenError(f"熔断器 {self.name} 处于开启状态")
        
        # 执行请求
        start_time = time.time()
        try:
            # 添加超时控制
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            # 记录成功
            response_time = (time.time() - start_time) * 1000
            await self._record_success(response_time)
            
            return result
            
        except Exception as e:
            # 记录失败
            await self._record_failure(e)
            raise
    
    async def _check_state(self) -> None:
        """检查并更新熔断器状态"""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.OPEN:
            # 检查是否可以尝试恢复
            if current_time >= self.next_attempt_time:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"熔断器 {self.name} 进入半开状态")
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # 半开状态下检查成功次数
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info(f"熔断器 {self.name} 恢复到关闭状态")
    
    async def _record_success(self, response_time: float) -> None:
        """记录成功请求"""
        async with self._lock:
            self.stats.update_success(response_time)
            self.recent_requests.append({
                'timestamp': time.time(),
                'success': True,
                'response_time': response_time
            })
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
            else:
                self.failure_count = max(0, self.failure_count - 1)
    
    async def _record_failure(self, error: Exception) -> None:
        """记录失败请求"""
        async with self._lock:
            error_type = type(error).__name__
            self.stats.update_failure(error_type)
            self.recent_requests.append({
                'timestamp': time.time(),
                'success': False,
                'error': error_type
            })
            
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # 检查是否需要开启熔断器
            if (self.state == CircuitBreakerState.CLOSED and 
                self.failure_count >= self.config.failure_threshold):
                
                self.state = CircuitBreakerState.OPEN
                self.next_attempt_time = time.time() + self.config.recovery_timeout
                logger.warning(f"熔断器 {self.name} 开启，将在 {self.config.recovery_timeout} 秒后尝试恢复")
            
            elif self.state == CircuitBreakerState.HALF_OPEN:
                # 半开状态下失败，重新开启
                self.state = CircuitBreakerState.OPEN
                self.next_attempt_time = time.time() + self.config.recovery_timeout
                logger.warning(f"熔断器 {self.name} 重新开启")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_requests': self.stats.total_requests,
            'failure_rate': self.stats.failure_rate,
            'avg_response_time': self.stats.avg_response_time,
            'last_failure_time': self.stats.last_failure_time,
            'last_success_time': self.stats.last_success_time,
            'error_types': dict(self.stats.error_types)
        }


class CircuitBreakerOpenError(Exception):
    """熔断器开启异常"""
    pass


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
    
    async def retry_with_backoff(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """带退避的重试"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"重试 {attempt + 1}/{self.config.max_retries}，{delay:.2f}秒后重试: {str(e)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"重试失败，已达到最大重试次数: {str(e)}")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算退避延迟"""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        # 添加抖动
        if self.config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class EnhancedErrorHandler:
    """增强错误处理器"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handler = None
        self.error_patterns: List[ErrorPattern] = []
        self.fallback_handlers: Dict[str, Callable] = {}
        
        # 错误统计
        self.global_stats = ErrorStatistics()
        self.error_history: deque = deque(maxlen=1000)
        
        # 配置
        self.default_config = CircuitBreakerConfig()
        
        # 初始化错误模式
        self._initialize_error_patterns()
    
    def _initialize_error_patterns(self) -> None:
        """初始化错误模式"""
        self.error_patterns = [
            ErrorPattern(
                error_type="ConnectionError",
                pattern="连接",
                severity=ErrorSeverity.HIGH,
                action="circuit_break"
            ),
            ErrorPattern(
                error_type="TimeoutError",
                pattern="超时",
                severity=ErrorSeverity.MEDIUM,
                action="retry"
            ),
            ErrorPattern(
                error_type="ValueError",
                pattern="参数错误",
                severity=ErrorSeverity.LOW,
                action="log_only"
            ),
            ErrorPattern(
                error_type="MemoryError",
                pattern="内存不足",
                severity=ErrorSeverity.CRITICAL,
                action="immediate_fallback"
            )
        ]
    
    def get_or_create_circuit_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self.circuit_breakers:
            circuit_config = config or self.default_config
            self.circuit_breakers[name] = CircuitBreaker(name, circuit_config)
        
        return self.circuit_breakers[name]
    
    def circuit_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> Callable:
        """熔断器装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                cb = self.get_or_create_circuit_breaker(name, config)
                return await cb.call(func, *args, **kwargs)
            return wrapper
        return decorator
    
    def retry_on_failure(
        self, 
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ) -> Callable:
        """重试装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                config = CircuitBreakerConfig(
                    max_retries=max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    exponential_base=exponential_base,
                    jitter=jitter
                )
                retry_handler = RetryHandler(config)
                return await retry_handler.retry_with_backoff(func, *args, **kwargs)
            return wrapper
        return decorator
    
    def with_fallback(self, fallback_func: Callable) -> Callable:
        """回退装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"主函数失败，使用回退方案: {str(e)}")
                    await self._record_error(e, func.__name__)
                    
                    try:
                        return await fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"回退方案也失败: {str(fallback_error)}")
                        raise e  # 抛出原始异常
            return wrapper
        return decorator
    
    async def handle_error(
        self, 
        error: Exception, 
        context: str = "",
        fallback_result: Any = None
    ) -> Any:
        """处理错误"""
        await self._record_error(error, context)
        
        # 分析错误模式
        pattern = self._analyze_error_pattern(error)
        
        if pattern:
            action = pattern.action
            
            if action == "circuit_break":
                # 触发熔断器
                cb_name = f"error_handler_{context}"
                cb = self.get_or_create_circuit_breaker(cb_name)
                await cb._record_failure(error)
                
            elif action == "retry":
                # 建议重试
                logger.info(f"建议重试操作: {context}")
                
            elif action == "immediate_fallback":
                # 立即回退
                if fallback_result is not None:
                    logger.warning(f"执行立即回退: {context}")
                    return fallback_result
                
            elif action == "log_only":
                # 仅记录日志
                logger.warning(f"记录错误: {context} - {str(error)}")
        
        # 默认重新抛出异常
        raise error
    
    async def _record_error(self, error: Exception, context: str) -> None:
        """记录错误"""
        error_record = {
            'timestamp': time.time(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'stack_trace': traceback.format_exc()
        }
        
        self.error_history.append(error_record)
        self.global_stats.update_failure(type(error).__name__)
        
        logger.error(f"错误记录 - 上下文: {context}, 错误: {str(error)}")
    
    def _analyze_error_pattern(self, error: Exception) -> Optional[ErrorPattern]:
        """分析错误模式"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        for pattern in self.error_patterns:
            if (pattern.error_type == error_type or 
                pattern.pattern.lower() in error_message):
                return pattern
        
        return None
    
    def register_fallback_handler(self, name: str, handler: Callable) -> None:
        """注册回退处理器"""
        self.fallback_handlers[name] = handler
        logger.info(f"注册回退处理器: {name}")
    
    async def execute_with_protection(
        self, 
        func: Callable,
        circuit_breaker_name: str,
        fallback_name: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """带保护机制执行函数"""
        try:
            # 使用熔断器保护
            cb = self.get_or_create_circuit_breaker(circuit_breaker_name)
            return await cb.call(func, *args, **kwargs)
            
        except CircuitBreakerOpenError:
            # 熔断器开启，使用回退
            if fallback_name and fallback_name in self.fallback_handlers:
                logger.info(f"熔断器开启，使用回退处理器: {fallback_name}")
                fallback_handler = self.fallback_handlers[fallback_name]
                return await fallback_handler(*args, **kwargs)
            else:
                raise
        
        except Exception as e:
            # 其他异常处理
            return await self.handle_error(e, circuit_breaker_name)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            'global_stats': {
                'total_requests': self.global_stats.total_requests,
                'failed_requests': self.global_stats.failed_requests,
                'success_requests': self.global_stats.success_requests,
                'failure_rate': self.global_stats.failure_rate,
                'error_types': dict(self.global_stats.error_types)
            },
            'circuit_breakers': {
                name: cb.get_stats() 
                for name, cb in self.circuit_breakers.items()
            },
            'recent_errors': list(self.error_history)[-10:],  # 最近10个错误
            'error_patterns': [
                {
                    'type': pattern.error_type,
                    'severity': pattern.severity.value,
                    'action': pattern.action
                }
                for pattern in self.error_patterns
            ]
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            'status': 'healthy',
            'circuit_breakers': {},
            'overall_failure_rate': self.global_stats.failure_rate,
            'timestamp': time.time()
        }
        
        # 检查熔断器状态
        unhealthy_breakers = 0
        for name, cb in self.circuit_breakers.items():
            cb_health = {
                'state': cb.state.value,
                'failure_rate': cb.stats.failure_rate,
                'last_failure': cb.stats.last_failure_time
            }
            
            if cb.state == CircuitBreakerState.OPEN:
                cb_health['status'] = 'unhealthy'
                unhealthy_breakers += 1
            elif cb.state == CircuitBreakerState.HALF_OPEN:
                cb_health['status'] = 'recovering'
            else:
                cb_health['status'] = 'healthy'
            
            health['circuit_breakers'][name] = cb_health
        
        # 整体健康状态判断
        if unhealthy_breakers > 0:
            health['status'] = 'degraded'
        
        if self.global_stats.failure_rate > 0.5:  # 失败率超过50%
            health['status'] = 'unhealthy'
        
        return health
    
    async def reset_circuit_breaker(self, name: str) -> bool:
        """重置熔断器"""
        if name in self.circuit_breakers:
            cb = self.circuit_breakers[name]
            async with cb._lock:
                cb.state = CircuitBreakerState.CLOSED
                cb.failure_count = 0
                cb.success_count = 0
                cb.stats = ErrorStatistics()
            
            logger.info(f"熔断器已重置: {name}")
            return True
        
        return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        # 清理熔断器
        self.circuit_breakers.clear()
        
        # 清理统计数据
        self.error_history.clear()
        self.global_stats = ErrorStatistics()
        
        logger.info("错误处理器清理完成")


# 全局错误处理器实例
_error_handler: Optional[EnhancedErrorHandler] = None


def get_error_handler() -> EnhancedErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    
    if _error_handler is None:
        _error_handler = EnhancedErrorHandler()
    
    return _error_handler


# 便捷装饰器
def circuit_breaker(name: str, **kwargs):
    """熔断器装饰器快捷方式"""
    handler = get_error_handler()
    config = CircuitBreakerConfig(**kwargs) if kwargs else None
    return handler.circuit_breaker(name, config)


def retry_on_failure(**kwargs):
    """重试装饰器快捷方式"""
    handler = get_error_handler()
    return handler.retry_on_failure(**kwargs)


def with_fallback(fallback_func):
    """回退装饰器快捷方式"""
    handler = get_error_handler()
    return handler.with_fallback(fallback_func) 