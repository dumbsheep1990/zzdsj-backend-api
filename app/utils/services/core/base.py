"""
Services模块核心基类
提供服务管理的抽象基类和通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class ServiceStatus(Enum):
    """服务状态枚举"""
    UNKNOWN = "unknown"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ServiceComponent(ABC):
    """
    服务组件抽象基类
    所有服务相关组件都应该继承此类
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.status = ServiceStatus.UNKNOWN
        self.metadata = {}
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化服务组件
        
        Returns:
            bool: 是否初始化成功
        """
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """
        启动服务
        
        Returns:
            bool: 是否启动成功
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        停止服务
        
        Returns:
            bool: 是否停止成功
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict[str, Any]: 健康状态信息
        """
        pass
    
    def get_status(self) -> ServiceStatus:
        """获取服务状态"""
        return self.status
    
    def set_status(self, status: ServiceStatus) -> None:
        """设置服务状态"""
        self.status = status
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取服务元数据"""
        return self.metadata.copy()
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """更新服务元数据"""
        self.metadata.update(metadata)


class ServiceInfo:
    """服务信息数据类"""
    
    def __init__(self, name: str, version: str = "1.0.0", 
                 description: str = "", endpoint: str = "",
                 status: ServiceStatus = ServiceStatus.UNKNOWN,
                 metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.version = version
        self.description = description
        self.endpoint = endpoint
        self.status = status
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInfo':
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            endpoint=data.get("endpoint", ""),
            status=ServiceStatus(data.get("status", "unknown")),
            metadata=data.get("metadata", {})
        ) 