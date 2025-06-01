"""
对象存储实现
基于新架构的对象存储组件
"""

from typing import List, Dict, Any, Optional, Union, BinaryIO
import logging
from ..core.base import ObjectStorage
from ..core.exceptions import ObjectStoreError, ConfigurationError

logger = logging.getLogger(__name__)


class ObjectStore(ObjectStorage):
    """
    通用对象存储实现
    支持多种对象存储后端
    """
    
    def __init__(self, name: str = "default", config: Optional[Dict[str, Any]] = None):
        """
        初始化对象存储
        
        参数:
            name: 存储名称
            config: 配置参数
        """
        super().__init__(name, config)
        self._backend = None
        self._backend_type = self.get_config("object_store_type", "minio")
    
    async def initialize(self) -> None:
        """初始化对象存储"""
        if self._initialized:
            return
        
        try:
            # 根据配置选择后端
            if self._backend_type.lower() == "minio":
                from .minio_adapter import MinioObjectStore
                self._backend = MinioObjectStore(f"{self.name}_minio", self.config)
            else:
                raise ConfigurationError(f"不支持的对象存储类型: {self._backend_type}")
            
            # 初始化后端
            await self._backend.initialize()
            self._initialized = True
            self.logger.info(f"对象存储初始化完成: {self._backend_type}")
            
        except Exception as e:
            self.logger.error(f"对象存储初始化失败: {str(e)}")
            raise ObjectStoreError(f"对象存储初始化失败: {str(e)}")
    
    async def connect(self) -> bool:
        """建立连接"""
        if not self._backend:
            await self.initialize()
        
        try:
            result = await self._backend.connect()
            self._connected = result
            return result
        except Exception as e:
            self.logger.error(f"对象存储连接失败: {str(e)}")
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._backend:
            await self._backend.disconnect()
        self._connected = False
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self._backend:
            return False
        return await self._backend.health_check()
    
    async def upload_object(self,
                          bucket: str,
                          key: str,
                          data: Union[bytes, BinaryIO],
                          content_type: Optional[str] = None,
                          metadata: Optional[Dict[str, str]] = None) -> str:
        """上传对象"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.upload_object(bucket, key, data, content_type, metadata)
        except Exception as e:
            self.logger.error(f"上传对象失败: {str(e)}")
            raise ObjectStoreError(f"上传对象失败: {str(e)}", bucket=bucket, key=key)
    
    async def download_object(self,
                            bucket: str,
                            key: str) -> Optional[bytes]:
        """下载对象"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.download_object(bucket, key)
        except Exception as e:
            self.logger.error(f"下载对象失败: {str(e)}")
            raise ObjectStoreError(f"下载对象失败: {str(e)}", bucket=bucket, key=key)
    
    async def delete_object(self,
                          bucket: str,
                          key: str) -> bool:
        """删除对象"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.delete_object(bucket, key)
        except Exception as e:
            self.logger.error(f"删除对象失败: {str(e)}")
            raise ObjectStoreError(f"删除对象失败: {str(e)}", bucket=bucket, key=key)
    
    async def get_object_url(self,
                           bucket: str,
                           key: str,
                           expires: int = 3600) -> str:
        """获取对象URL"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.get_object_url(bucket, key, expires)
        except Exception as e:
            self.logger.error(f"获取对象URL失败: {str(e)}")
            raise ObjectStoreError(f"获取对象URL失败: {str(e)}", bucket=bucket, key=key)
    
    async def list_objects(self,
                         bucket: str,
                         prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出对象"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.list_objects(bucket, prefix)
        except Exception as e:
            self.logger.error(f"列出对象失败: {str(e)}")
            raise ObjectStoreError(f"列出对象失败: {str(e)}", bucket=bucket)


# 全局对象存储实例
_global_object_store: Optional[ObjectStore] = None


def get_object_store(config: Optional[Dict[str, Any]] = None) -> ObjectStore:
    """
    获取全局对象存储实例
    
    参数:
        config: 配置参数
        
    返回:
        对象存储实例
    """
    global _global_object_store
    
    if _global_object_store is None or config is not None:
        _global_object_store = ObjectStore("global", config)
    
    return _global_object_store


def create_object_store(name: str, config: Dict[str, Any]) -> ObjectStore:
    """
    创建对象存储实例
    
    参数:
        name: 存储名称
        config: 配置参数
        
    返回:
        对象存储实例
    """
    return ObjectStore(name, config) 