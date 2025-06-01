"""
向量存储实现
基于新架构的向量存储组件
"""

from typing import List, Dict, Any, Optional, Union
import logging
from ..core.base import VectorStorage
from ..core.exceptions import VectorStoreError, ConfigurationError

logger = logging.getLogger(__name__)


class VectorStore(VectorStorage):
    """
    通用向量存储实现
    支持多种向量数据库后端
    """
    
    def __init__(self, name: str = "default", config: Optional[Dict[str, Any]] = None):
        """
        初始化向量存储
        
        参数:
            name: 存储名称
            config: 配置参数
        """
        super().__init__(name, config)
        self._backend = None
        self._backend_type = self.get_config("vector_store_type", "milvus")
    
    async def initialize(self) -> None:
        """初始化向量存储"""
        if self._initialized:
            return
        
        try:
            # 根据配置选择后端
            if self._backend_type.lower() == "milvus":
                from .milvus_adapter import MilvusVectorStore
                self._backend = MilvusVectorStore(f"{self.name}_milvus", self.config)
            else:
                raise ConfigurationError(f"不支持的向量存储类型: {self._backend_type}")
            
            # 初始化后端
            await self._backend.initialize()
            self._initialized = True
            self.logger.info(f"向量存储初始化完成: {self._backend_type}")
            
        except Exception as e:
            self.logger.error(f"向量存储初始化失败: {str(e)}")
            raise VectorStoreError(f"向量存储初始化失败: {str(e)}")
    
    async def connect(self) -> bool:
        """建立连接"""
        if not self._backend:
            await self.initialize()
        
        try:
            result = await self._backend.connect()
            self._connected = result
            return result
        except Exception as e:
            self.logger.error(f"向量存储连接失败: {str(e)}")
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
    
    async def create_collection(self, name: str, dimension: int, **kwargs) -> bool:
        """创建向量集合"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.create_collection(name, dimension, **kwargs)
        except Exception as e:
            self.logger.error(f"创建集合失败: {str(e)}")
            raise VectorStoreError(f"创建集合失败: {str(e)}", collection=name)
    
    async def add_vectors(self, 
                         collection: str,
                         vectors: List[List[float]], 
                         ids: Optional[List[Union[int, str]]] = None,
                         metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """添加向量"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.add_vectors(collection, vectors, ids, metadata)
        except Exception as e:
            self.logger.error(f"添加向量失败: {str(e)}")
            raise VectorStoreError(f"添加向量失败: {str(e)}", collection=collection)
    
    async def search_vectors(self,
                           collection: str,
                           query_vector: List[float],
                           top_k: int = 10,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.search_vectors(collection, query_vector, top_k, filters)
        except Exception as e:
            self.logger.error(f"搜索向量失败: {str(e)}")
            raise VectorStoreError(f"搜索向量失败: {str(e)}", collection=collection)
    
    async def delete_vectors(self,
                           collection: str,
                           ids: List[Union[int, str]]) -> bool:
        """删除向量"""
        if not self._backend:
            await self.initialize()
        
        try:
            return await self._backend.delete_vectors(collection, ids)
        except Exception as e:
            self.logger.error(f"删除向量失败: {str(e)}")
            raise VectorStoreError(f"删除向量失败: {str(e)}", collection=collection)


# 全局向量存储实例
_global_vector_store: Optional[VectorStore] = None


def get_vector_store(config: Optional[Dict[str, Any]] = None) -> VectorStore:
    """
    获取全局向量存储实例
    
    参数:
        config: 配置参数
        
    返回:
        向量存储实例
    """
    global _global_vector_store
    
    if _global_vector_store is None or config is not None:
        _global_vector_store = VectorStore("global", config)
    
    return _global_vector_store


def create_vector_store(name: str, config: Dict[str, Any]) -> VectorStore:
    """
    创建向量存储实例
    
    参数:
        name: 存储名称
        config: 配置参数
        
    返回:
        向量存储实例
    """
    return VectorStore(name, config) 