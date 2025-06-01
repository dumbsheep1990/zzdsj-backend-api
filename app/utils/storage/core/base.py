"""
存储组件抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, BinaryIO, Union
import logging
import time

logger = logging.getLogger(__name__)


class StorageComponent(ABC):
    """
    存储组件抽象基类
    所有存储相关组件的基础类
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化存储组件
        
        参数:
            name: 组件名称
            config: 配置参数字典
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{name}")
        self._initialized = False
        self._connected = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化组件
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        建立连接
        子类必须实现此方法
        
        返回:
            连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        断开连接
        子类必须实现此方法
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查
        子类必须实现此方法
        
        返回:
            健康状态
        """
        pass
    
    def is_initialized(self) -> bool:
        """检查组件是否已初始化"""
        return self._initialized
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self.config.update(config)
        self.logger.info(f"配置已更新: {list(config.keys())}")


class VectorStorage(StorageComponent):
    """
    向量存储抽象基类
    定义向量存储的标准接口
    """
    
    @abstractmethod
    async def create_collection(self, name: str, dimension: int, **kwargs) -> bool:
        """
        创建向量集合
        
        参数:
            name: 集合名称
            dimension: 向量维度
            **kwargs: 其他参数
            
        返回:
            是否创建成功
        """
        pass
    
    @abstractmethod
    async def add_vectors(self, 
                         collection: str,
                         vectors: List[List[float]], 
                         ids: Optional[List[Union[int, str]]] = None,
                         metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        添加向量
        
        参数:
            collection: 集合名称
            vectors: 向量列表
            ids: ID列表
            metadata: 元数据列表
            
        返回:
            是否添加成功
        """
        pass
    
    @abstractmethod
    async def search_vectors(self,
                           collection: str,
                           query_vector: List[float],
                           top_k: int = 10,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        搜索相似向量
        
        参数:
            collection: 集合名称
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 过滤条件
            
        返回:
            搜索结果列表
        """
        pass
    
    @abstractmethod
    async def delete_vectors(self,
                           collection: str,
                           ids: List[Union[int, str]]) -> bool:
        """
        删除向量
        
        参数:
            collection: 集合名称
            ids: 要删除的ID列表
            
        返回:
            是否删除成功
        """
        pass


class ObjectStorage(StorageComponent):
    """
    对象存储抽象基类
    定义对象存储的标准接口
    """
    
    @abstractmethod
    async def upload_object(self,
                          bucket: str,
                          key: str,
                          data: Union[bytes, BinaryIO],
                          content_type: Optional[str] = None,
                          metadata: Optional[Dict[str, str]] = None) -> str:
        """
        上传对象
        
        参数:
            bucket: 存储桶名称
            key: 对象键
            data: 对象数据
            content_type: 内容类型
            metadata: 元数据
            
        返回:
            对象URL
        """
        pass
    
    @abstractmethod
    async def download_object(self,
                            bucket: str,
                            key: str) -> Optional[bytes]:
        """
        下载对象
        
        参数:
            bucket: 存储桶名称
            key: 对象键
            
        返回:
            对象数据
        """
        pass
    
    @abstractmethod
    async def delete_object(self,
                          bucket: str,
                          key: str) -> bool:
        """
        删除对象
        
        参数:
            bucket: 存储桶名称
            key: 对象键
            
        返回:
            是否删除成功
        """
        pass
    
    @abstractmethod
    async def get_object_url(self,
                           bucket: str,
                           key: str,
                           expires: int = 3600) -> str:
        """
        获取对象URL
        
        参数:
            bucket: 存储桶名称
            key: 对象键
            expires: 过期时间（秒）
            
        返回:
            对象URL
        """
        pass
    
    @abstractmethod
    async def list_objects(self,
                         bucket: str,
                         prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出对象
        
        参数:
            bucket: 存储桶名称
            prefix: 前缀过滤
            
        返回:
            对象列表
        """
        pass 