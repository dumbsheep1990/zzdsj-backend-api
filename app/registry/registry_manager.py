"""
注册管理器
提供统一工具注册中心的配置和管理功能
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from ..abstractions import FrameworkConfig
from .unified_registry import UnifiedToolRegistry, ToolRegistryError


class RegistryStatus(str, Enum):
    """注册表状态"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class RegistryConfig:
    """注册表配置"""
    # 基本配置
    auto_initialize: bool = True
    enable_health_check: bool = True
    health_check_interval: int = 60  # 秒
    
    # 性能配置
    max_concurrent_executions: int = 50
    execution_timeout: int = 300  # 秒
    adapter_initialization_timeout: int = 30  # 秒
    
    # 缓存配置
    enable_tool_cache: bool = True
    cache_ttl: int = 3600  # 秒
    
    # 日志配置
    log_level: str = "INFO"
    enable_execution_logging: bool = True
    
    # 框架配置
    framework_configs: Dict[str, FrameworkConfig] = field(default_factory=dict)
    
    # 监控配置
    enable_metrics: bool = True
    metrics_collection_interval: int = 30  # 秒
    
    # 自定义配置
    custom_config: Dict[str, Any] = field(default_factory=dict)


class RegistryManager:
    """注册管理器 - 管理统一工具注册中心的生命周期"""
    
    def __init__(self, config: Optional[RegistryConfig] = None):
        self.config = config or RegistryConfig()
        self._logger = logging.getLogger(__name__)
        
        # 核心组件
        self._registry: Optional[UnifiedToolRegistry] = None
        self._status = RegistryStatus.UNINITIALIZED
        
        # 健康检查任务
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics_collection_task: Optional[asyncio.Task] = None
        
        # 运行时状态
        self._start_time: Optional[datetime] = None
        self._last_health_check: Optional[datetime] = None
        self._health_status = {"healthy": False, "last_check": None, "errors": []}
        
        # 指标收集
        self._metrics_history: List[Dict[str, Any]] = []
    
    async def initialize(self) -> bool:
        """初始化注册管理器"""
        try:
            self._status = RegistryStatus.INITIALIZING
            self._start_time = datetime.now()
            
            # 配置日志级别
            logging.getLogger().setLevel(getattr(logging, self.config.log_level))
            
            # 创建注册中心
            self._registry = UnifiedToolRegistry()
            
            # 初始化注册中心
            await asyncio.wait_for(
                self._registry.initialize(),
                timeout=self.config.adapter_initialization_timeout
            )
            
            # 启动后台任务
            if self.config.enable_health_check:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            if self.config.enable_metrics:
                self._metrics_collection_task = asyncio.create_task(self._metrics_collection_loop())
            
            self._status = RegistryStatus.READY
            self._logger.info("Registry manager initialized successfully")
            return True
            
        except asyncio.TimeoutError:
            self._status = RegistryStatus.ERROR
            error_msg = f"Registry initialization timeout after {self.config.adapter_initialization_timeout}s"
            self._logger.error(error_msg)
            raise ToolRegistryError(error_msg, "INIT_TIMEOUT")
            
        except Exception as e:
            self._status = RegistryStatus.ERROR
            self._logger.error(f"Failed to initialize registry manager: {e}")
            raise ToolRegistryError(f"Initialization failed: {e}", "INIT_ERROR")
    
    async def shutdown(self) -> bool:
        """关闭注册管理器"""
        try:
            self._logger.info("Shutting down registry manager...")
            
            # 停止后台任务
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            if self._metrics_collection_task:
                self._metrics_collection_task.cancel()
                try:
                    await self._metrics_collection_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭注册中心
            if self._registry:
                await self._registry.shutdown()
            
            self._status = RegistryStatus.SHUTDOWN
            self._logger.info("Registry manager shutdown successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to shutdown registry manager: {e}")
            return False
    
    @property
    def status(self) -> RegistryStatus:
        """获取状态"""
        return self._status
    
    @property
    def registry(self) -> Optional[UnifiedToolRegistry]:
        """获取注册中心实例"""
        return self._registry
    
    @property
    def is_ready(self) -> bool:
        """检查是否就绪"""
        return self._status == RegistryStatus.READY and self._registry is not None
    
    def get_uptime(self) -> Optional[float]:
        """获取运行时间（秒）"""
        if not self._start_time:
            return None
        return (datetime.now() - self._start_time).total_seconds()
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            **self._health_status,
            "uptime_seconds": self.get_uptime(),
            "status": self._status.value,
            "registry_initialized": self._registry is not None and self._registry._initialized
        }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合状态信息"""
        base_status = {
            "manager_status": self._status.value,
            "manager_uptime": self.get_uptime(),
            "health_status": self.get_health_status(),
            "config": {
                "auto_initialize": self.config.auto_initialize,
                "max_concurrent_executions": self.config.max_concurrent_executions,
                "execution_timeout": self.config.execution_timeout,
                "enable_health_check": self.config.enable_health_check,
                "enable_metrics": self.config.enable_metrics
            }
        }
        
        # 添加注册中心状态
        if self._registry:
            base_status["registry_stats"] = self._registry.get_registry_stats()
        
        # 添加最新指标
        if self._metrics_history:
            base_status["latest_metrics"] = self._metrics_history[-1]
        
        return base_status
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Health check failed: {e}")
    
    async def _perform_health_check(self):
        """执行健康检查"""
        try:
            self._last_health_check = datetime.now()
            errors = []
            
            # 检查注册中心状态
            if not self._registry or not self._registry._initialized:
                errors.append("Registry not initialized")
            
            # 检查适配器状态
            if self._registry:
                stats = self._registry.get_registry_stats()
                if stats["frameworks_count"] == 0:
                    errors.append("No frameworks registered")
                
                if stats["total_tools"] == 0:
                    errors.append("No tools registered")
            
            # 更新健康状态
            self._health_status = {
                "healthy": len(errors) == 0,
                "last_check": self._last_health_check.isoformat(),
                "errors": errors
            }
            
            if errors:
                self._logger.warning(f"Health check issues: {errors}")
            
        except Exception as e:
            self._health_status = {
                "healthy": False,
                "last_check": datetime.now().isoformat(),
                "errors": [f"Health check error: {str(e)}"]
            }
    
    async def _metrics_collection_loop(self):
        """指标收集循环"""
        while True:
            try:
                await asyncio.sleep(self.config.metrics_collection_interval)
                await self._collect_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Metrics collection failed: {e}")
    
    async def _collect_metrics(self):
        """收集指标"""
        try:
            if not self._registry:
                return
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": self.get_uptime(),
                "registry_stats": self._registry.get_registry_stats(),
                "health_status": self._health_status,
                "config_snapshot": {
                    "max_concurrent_executions": self.config.max_concurrent_executions,
                    "execution_timeout": self.config.execution_timeout
                }
            }
            
            # 保留最近的100个指标记录
            self._metrics_history.append(metrics)
            if len(self._metrics_history) > 100:
                self._metrics_history.pop(0)
            
        except Exception as e:
            self._logger.error(f"Failed to collect metrics: {e}")
    
    def get_metrics_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取指标历史"""
        return self._metrics_history[-limit:] if self._metrics_history else [] 