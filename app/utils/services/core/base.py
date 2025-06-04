"""
Services模块核心基类
提供服务管理的抽象基类和通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


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
    支持异步上下文管理器和生命周期管理
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.status = ServiceStatus.UNKNOWN
        self.metadata = {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{name}")
        self._start_time = None
        self._stop_time = None
        self._error_count = 0
        self._last_error = None
    
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
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()
        return False
    
    async def restart(self) -> bool:
        """
        重启服务
        
        Returns:
            bool: 是否重启成功
        """
        self.logger.info(f"正在重启服务: {self.name}")
        
        # 先停止服务
        stop_success = await self.stop()
        if not stop_success:
            self.logger.error(f"停止服务 {self.name} 失败")
            return False
        
        # 等待一段时间确保完全停止
        await asyncio.sleep(1)
        
        # 重新启动服务
        start_success = await self.start()
        if start_success:
            self.logger.info(f"服务 {self.name} 重启成功")
        else:
            self.logger.error(f"启动服务 {self.name} 失败")
        
        return start_success
    
    def get_status(self) -> ServiceStatus:
        """获取服务状态"""
        return self.status
    
    def set_status(self, status: ServiceStatus) -> None:
        """设置服务状态"""
        old_status = self.status
        self.status = status
        
        # 记录状态变更时间
        if status == ServiceStatus.RUNNING and self._start_time is None:
            self._start_time = datetime.now()
        elif status == ServiceStatus.STOPPED:
            self._stop_time = datetime.now()
        
        self.logger.info(f"服务 {self.name} 状态变更: {old_status.value} -> {status.value}")
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取服务元数据"""
        metadata = self.metadata.copy()
        
        # 添加运行时信息
        metadata.update({
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "stop_time": self._stop_time.isoformat() if self._stop_time else None,
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
            "error_count": self._error_count,
            "last_error": self._last_error
        })
        
        return metadata
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """更新服务元数据"""
        self.metadata.update(metadata)
    
    def record_error(self, error: Union[str, Exception]) -> None:
        """记录错误信息"""
        self._error_count += 1
        self._last_error = {
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
            "type": type(error).__name__ if isinstance(error, Exception) else "Error"
        }
        self.logger.error(f"服务 {self.name} 发生错误: {error}")
    
    def reset_error_count(self) -> None:
        """重置错误计数"""
        self._error_count = 0
        self._last_error = None
        self.logger.info(f"服务 {self.name} 错误计数已重置")


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
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "endpoint": self.endpoint,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInfo':
        """从字典创建"""
        instance = cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            endpoint=data.get("endpoint", ""),
            status=ServiceStatus(data.get("status", "unknown")),
            metadata=data.get("metadata", {})
        )
        
        # 如果有创建时间，则解析
        if "created_at" in data:
            try:
                instance.created_at = datetime.fromisoformat(data["created_at"])
            except:
                pass
        
        return instance
    
    def update_status(self, status: ServiceStatus) -> None:
        """更新服务状态"""
        self.status = status
        self.metadata["last_updated"] = datetime.now().isoformat()


class ServiceRegistry:
    """服务注册表"""
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._lock = asyncio.Lock()
    
    async def register(self, service_info: ServiceInfo) -> bool:
        """注册服务"""
        async with self._lock:
            if service_info.name in self._services:
                logger.warning(f"服务 {service_info.name} 已存在，将被覆盖")
            
            self._services[service_info.name] = service_info
            logger.info(f"服务 {service_info.name} 已注册")
            return True
    
    async def unregister(self, service_name: str) -> bool:
        """注销服务"""
        async with self._lock:
            if service_name in self._services:
                del self._services[service_name]
                logger.info(f"服务 {service_name} 已注销")
                return True
            return False
    
    async def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """获取服务信息"""
        async with self._lock:
            return self._services.get(service_name)
    
    async def list_services(self) -> List[ServiceInfo]:
        """列出所有服务"""
        async with self._lock:
            return list(self._services.values())
    
    async def get_services_by_status(self, status: ServiceStatus) -> List[ServiceInfo]:
        """根据状态获取服务列表"""
        async with self._lock:
            return [service for service in self._services.values() if service.status == status] 