"""
监控组件抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class MonitoringComponent(ABC):
    """
    监控组件抽象基类
    所有监控相关组件的基础类
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化监控组件
        
        参数:
            name: 组件名称
            config: 配置参数字典
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{name}")
        self._initialized = False
        self._start_time = time.time()
        self._last_check_time = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化组件
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def collect_metrics(self) -> Dict[str, Any]:
        """
        收集指标数据
        子类必须实现此方法
        
        返回:
            指标数据字典
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        执行健康检查
        子类必须实现此方法
        
        返回:
            健康状态
        """
        pass
    
    def is_initialized(self) -> bool:
        """
        检查组件是否已初始化
        
        返回:
            是否已初始化
        """
        return self._initialized
    
    def get_uptime(self) -> float:
        """
        获取组件运行时间（秒）
        
        返回:
            运行时间
        """
        return time.time() - self._start_time
    
    def get_last_check_time(self) -> Optional[datetime]:
        """
        获取上次检查时间
        
        返回:
            上次检查时间
        """
        if self._last_check_time:
            return datetime.fromtimestamp(self._last_check_time)
        return None
    
    def update_last_check_time(self) -> None:
        """更新上次检查时间"""
        self._last_check_time = time.time()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        参数:
            key: 配置键
            default: 默认值
            
        返回:
            配置值
        """
        return self.config.get(key, default)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        更新配置
        
        参数:
            config: 新配置参数
        """
        self.config.update(config)
        self.logger.info(f"配置已更新: {list(config.keys())}")
    
    async def get_status(self) -> Dict[str, Any]:
        """
        获取组件状态信息
        
        返回:
            状态信息字典
        """
        try:
            health = await self.health_check()
            metrics = await self.collect_metrics()
            
            return {
                "name": self.name,
                "initialized": self._initialized,
                "healthy": health,
                "uptime": self.get_uptime(),
                "last_check": self.get_last_check_time().isoformat() if self._last_check_time else None,
                "metrics": metrics
            }
        except Exception as e:
            self.logger.error(f"获取状态失败: {str(e)}")
            return {
                "name": self.name,
                "initialized": self._initialized,
                "healthy": False,
                "error": str(e),
                "uptime": self.get_uptime()
            } 