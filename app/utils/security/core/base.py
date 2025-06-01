"""
安全组件抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SecurityComponent(ABC):
    """
    安全组件抽象基类
    所有安全相关组件的基础类
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化安全组件
        
        参数:
            config: 配置参数字典
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化组件
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def check(self, *args, **kwargs) -> Any:
        """
        执行安全检查
        子类必须实现此方法
        """
        pass
    
    def is_initialized(self) -> bool:
        """
        检查组件是否已初始化
        
        返回:
            是否已初始化
        """
        return self._initialized
    
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