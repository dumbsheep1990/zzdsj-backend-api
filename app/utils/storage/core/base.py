"""
存储组件抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, BinaryIO, Union
import logging
import time
import asyncio
from datetime import datetime

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
        self._last_health_check = None
        self._health_status = None
    
    async def initialize(self) -> None:
        """
        初始化组件
        执行组件启动所需的初始化操作
        """
        try:
            self.logger.info(f"开始初始化存储组件: {self.name}")
            
            # 验证必要的配置项
            await self._validate_config()
            
            # 执行具体的初始化逻辑
            await self._do_initialize()
            
            # 标记为已初始化
            self._initialized = True
            self.logger.info(f"存储组件初始化完成: {self.name}")
            
        except Exception as e:
            self.logger.error(f"存储组件初始化失败: {self.name}, 错误: {str(e)}")
            self._initialized = False
            raise
    
    async def connect(self) -> bool:
        """
        建立连接
        建立与底层存储服务的连接
        
        返回:
            连接是否成功
        """
        try:
            if not self._initialized:
                await self.initialize()
            
            self.logger.info(f"正在连接存储服务: {self.name}")
            
            # 执行具体的连接逻辑
            success = await self._do_connect()
            
            if success:
                self._connected = True
                self.logger.info(f"存储服务连接成功: {self.name}")
                
                # 连接成功后执行健康检查
                await self.health_check()
            else:
                self.logger.warning(f"存储服务连接失败: {self.name}")
                self._connected = False
            
            return success
            
        except Exception as e:
            self.logger.error(f"连接存储服务时出错: {self.name}, 错误: {str(e)}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """
        断开连接
        安全地断开与底层存储服务的连接
        """
        try:
            if not self._connected:
                self.logger.debug(f"存储服务未连接，无需断开: {self.name}")
                return
            
            self.logger.info(f"正在断开存储服务连接: {self.name}")
            
            # 执行具体的断开连接逻辑
            await self._do_disconnect()
            
            # 清理连接状态
            self._connected = False
            self._health_status = None
            self.logger.info(f"存储服务连接已断开: {self.name}")
            
        except Exception as e:
            self.logger.error(f"断开存储服务连接时出错: {self.name}, 错误: {str(e)}")
            # 即使出错也要清理状态
            self._connected = False
    
    async def health_check(self) -> bool:
        """
        健康检查
        检查存储服务的健康状态
        
        返回:
            健康状态
        """
        try:
            if not self._connected:
                self.logger.debug(f"存储服务未连接，跳过健康检查: {self.name}")
                self._health_status = False
                return False
            
            # 避免频繁的健康检查，最小间隔10秒
            now = datetime.now()
            if (self._last_health_check and 
                (now - self._last_health_check).total_seconds() < 10):
                return self._health_status or False
            
            self.logger.debug(f"执行健康检查: {self.name}")
            
            # 执行具体的健康检查逻辑
            start_time = time.time()
            is_healthy = await self._do_health_check()
            check_duration = time.time() - start_time
            
            # 更新健康状态
            self._health_status = is_healthy
            self._last_health_check = now
            
            if is_healthy:
                self.logger.debug(f"健康检查通过: {self.name}, 耗时: {check_duration:.2f}s")
            else:
                self.logger.warning(f"健康检查失败: {self.name}")
                
            return is_healthy
            
        except Exception as e:
            self.logger.error(f"健康检查时出错: {self.name}, 错误: {str(e)}")
            self._health_status = False
            return False
    
    # ========== 抽象方法，子类必须实现 ==========
    
    @abstractmethod
    async def _validate_config(self) -> None:
        """验证配置的有效性，子类实现具体的验证逻辑"""
        pass
    
    @abstractmethod
    async def _do_initialize(self) -> None:
        """执行具体的初始化逻辑，子类实现"""
        pass
    
    @abstractmethod
    async def _do_connect(self) -> bool:
        """执行具体的连接逻辑，子类实现"""
        pass
    
    @abstractmethod
    async def _do_disconnect(self) -> None:
        """执行具体的断开连接逻辑，子类实现"""
        pass
    
    @abstractmethod
    async def _do_health_check(self) -> bool:
        """执行具体的健康检查逻辑，子类实现"""
        pass
    
    # ========== 工具方法 ==========
    
    def is_initialized(self) -> bool:
        """检查组件是否已初始化"""
        return self._initialized
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    def is_healthy(self) -> Optional[bool]:
        """获取最近的健康状态"""
        return self._health_status
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        self.config.update(config)
        self.logger.info(f"配置已更新: {list(config.keys())}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取组件状态信息"""
        return {
            "name": self.name,
            "initialized": self._initialized,
            "connected": self._connected,
            "healthy": self._health_status,
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }


class VectorStorage(StorageComponent):
    """
    向量存储抽象基类
    定义向量存储的标准接口
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """初始化向量存储组件"""
        super().__init__(name, config)
        self._collections = set()  # 跟踪已创建的集合
        self._default_dimension = config.get('default_dimension', 1536) if config else 1536
    
    async def create_collection(self, name: str, dimension: int, **kwargs) -> bool:
        """
        创建向量集合
        
        参数:
            name: 集合名称
            dimension: 向量维度
            **kwargs: 其他参数如索引类型、距离度量等
            
        返回:
            是否创建成功
        """
        try:
            if not self._connected:
                await self.connect()
            
            self.logger.info(f"创建向量集合: {name}, 维度: {dimension}")
            
            # 检查集合是否已存在
            if await self.collection_exists(name):
                self.logger.warning(f"集合已存在: {name}")
                return True
            
            # 验证参数
            if dimension <= 0:
                raise ValueError(f"向量维度必须大于0: {dimension}")
            
            # 执行具体的创建逻辑
            success = await self._do_create_collection(name, dimension, **kwargs)
            
            if success:
                self._collections.add(name)
                self.logger.info(f"向量集合创建成功: {name}")
            else:
                self.logger.error(f"向量集合创建失败: {name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"创建向量集合时出错: {name}, 错误: {str(e)}")
            return False
    
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
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not vectors:
                raise ValueError("向量列表不能为空")
            
            if not await self.collection_exists(collection):
                raise ValueError(f"集合不存在: {collection}")
            
            # 验证向量维度一致性
            if vectors and len(vectors) > 0:
                vector_dim = len(vectors[0])
                for i, vector in enumerate(vectors):
                    if len(vector) != vector_dim:
                        raise ValueError(f"向量维度不一致，索引 {i}: 期望 {vector_dim}, 实际 {len(vector)}")
            
            # 验证ID数量匹配
            if ids and len(ids) != len(vectors):
                raise ValueError(f"ID数量与向量数量不匹配: {len(ids)} vs {len(vectors)}")
            
            # 验证元数据数量匹配
            if metadata and len(metadata) != len(vectors):
                raise ValueError(f"元数据数量与向量数量不匹配: {len(metadata)} vs {len(vectors)}")
            
            self.logger.info(f"添加向量到集合: {collection}, 数量: {len(vectors)}")
            
            # 执行具体的添加逻辑
            success = await self._do_add_vectors(collection, vectors, ids, metadata)
            
            if success:
                self.logger.info(f"向量添加成功: {collection}, 数量: {len(vectors)}")
            else:
                self.logger.error(f"向量添加失败: {collection}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"添加向量时出错: {collection}, 错误: {str(e)}")
            return False
    
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
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not query_vector:
                raise ValueError("查询向量不能为空")
            
            if top_k <= 0:
                raise ValueError(f"top_k必须大于0: {top_k}")
            
            if not await self.collection_exists(collection):
                raise ValueError(f"集合不存在: {collection}")
            
            self.logger.debug(f"搜索向量: {collection}, top_k: {top_k}")
            
            # 执行具体的搜索逻辑
            results = await self._do_search_vectors(collection, query_vector, top_k, filters)
            
            self.logger.debug(f"向量搜索完成: {collection}, 返回 {len(results)} 个结果")
            
            return results
            
        except Exception as e:
            self.logger.error(f"搜索向量时出错: {collection}, 错误: {str(e)}")
            return []
    
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
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not ids:
                raise ValueError("ID列表不能为空")
            
            if not await self.collection_exists(collection):
                raise ValueError(f"集合不存在: {collection}")
            
            self.logger.info(f"删除向量: {collection}, 数量: {len(ids)}")
            
            # 执行具体的删除逻辑
            success = await self._do_delete_vectors(collection, ids)
            
            if success:
                self.logger.info(f"向量删除成功: {collection}, 数量: {len(ids)}")
            else:
                self.logger.error(f"向量删除失败: {collection}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除向量时出错: {collection}, 错误: {str(e)}")
            return False
    
    async def collection_exists(self, name: str) -> bool:
        """
        检查集合是否存在
        
        参数:
            name: 集合名称
            
        返回:
            集合是否存在
        """
        try:
            if not self._connected:
                await self.connect()
            
            return await self._do_collection_exists(name)
            
        except Exception as e:
            self.logger.error(f"检查集合存在性时出错: {name}, 错误: {str(e)}")
            return False
    
    async def list_collections(self) -> List[str]:
        """
        列出所有集合
        
        返回:
            集合名称列表
        """
        try:
            if not self._connected:
                await self.connect()
            
            collections = await self._do_list_collections()
            self.logger.debug(f"列出集合: {len(collections)} 个")
            
            return collections
            
        except Exception as e:
            self.logger.error(f"列出集合时出错: {str(e)}")
            return []
    
    async def get_collection_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取集合信息
        
        参数:
            name: 集合名称
            
        返回:
            集合信息字典
        """
        try:
            if not await self.collection_exists(name):
                return None
            
            return await self._do_get_collection_info(name)
            
        except Exception as e:
            self.logger.error(f"获取集合信息时出错: {name}, 错误: {str(e)}")
            return None
    
    async def delete_collection(self, name: str) -> bool:
        """
        删除集合
        
        参数:
            name: 集合名称
            
        返回:
            是否删除成功
        """
        try:
            if not self._connected:
                await self.connect()
            
            # 检查集合是否存在
            if not await self.collection_exists(name):
                self.logger.warning(f"集合不存在，无需删除: {name}")
                return True
            
            self.logger.info(f"删除向量集合: {name}")
            
            # 执行具体的删除逻辑
            success = await self._do_delete_collection(name)
            
            if success:
                # 从本地缓存中移除
                self._collections.discard(name)
                self.logger.info(f"向量集合删除成功: {name}")
            else:
                self.logger.error(f"向量集合删除失败: {name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除向量集合时出错: {name}, 错误: {str(e)}")
            return False
    
    async def get_vector_count(self, collection: str) -> int:
        """
        获取集合中向量数量
        
        参数:
            collection: 集合名称
            
        返回:
            向量数量
        """
        try:
            if not await self.collection_exists(collection):
                return 0
            
            return await self._do_get_vector_count(collection)
            
        except Exception as e:
            self.logger.error(f"获取向量数量时出错: {collection}, 错误: {str(e)}")
            return 0
    
    # ========== 抽象方法，子类必须实现 ==========
    
    @abstractmethod
    async def _do_create_collection(self, name: str, dimension: int, **kwargs) -> bool:
        """执行具体的创建集合逻辑"""
        pass
    
    @abstractmethod
    async def _do_add_vectors(self, collection: str, vectors: List[List[float]], 
                            ids: Optional[List[Union[int, str]]], 
                            metadata: Optional[List[Dict[str, Any]]]) -> bool:
        """执行具体的添加向量逻辑"""
        pass
    
    @abstractmethod
    async def _do_search_vectors(self, collection: str, query_vector: List[float],
                               top_k: int, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行具体的搜索向量逻辑"""
        pass
    
    @abstractmethod
    async def _do_delete_vectors(self, collection: str, ids: List[Union[int, str]]) -> bool:
        """执行具体的删除向量逻辑"""
        pass
    
    @abstractmethod
    async def _do_collection_exists(self, name: str) -> bool:
        """执行具体的检查集合存在性逻辑"""
        pass
    
    @abstractmethod
    async def _do_list_collections(self) -> List[str]:
        """执行具体的列出集合逻辑"""
        pass
    
    @abstractmethod
    async def _do_get_collection_info(self, name: str) -> Dict[str, Any]:
        """执行具体的获取集合信息逻辑"""
        pass
    
    @abstractmethod
    async def _do_delete_collection(self, name: str) -> bool:
        """执行具体的删除集合逻辑"""
        pass
    
    @abstractmethod
    async def _do_get_vector_count(self, collection: str) -> int:
        """执行具体的获取向量数量逻辑"""
        pass


class ObjectStorage(StorageComponent):
    """
    对象存储抽象基类
    定义对象存储的标准接口
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """初始化对象存储组件"""
        super().__init__(name, config)
        self._buckets = set()  # 跟踪已创建的存储桶
        self._default_bucket = config.get('default_bucket', 'default') if config else 'default'
        self._upload_timeout = config.get('upload_timeout', 300) if config else 300
        self._download_timeout = config.get('download_timeout', 120) if config else 120
    
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
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not bucket:
                raise ValueError("存储桶名称不能为空")
            
            if not key:
                raise ValueError("对象键不能为空")
            
            if not data:
                raise ValueError("对象数据不能为空")
            
            # 确保存储桶存在
            if not await self.bucket_exists(bucket):
                await self.create_bucket(bucket)
            
            self.logger.info(f"上传对象: {bucket}/{key}")
            
            # 执行具体的上传逻辑
            object_url = await self._do_upload_object(bucket, key, data, content_type, metadata)
            
            if object_url:
                self.logger.info(f"对象上传成功: {bucket}/{key} -> {object_url}")
            else:
                self.logger.error(f"对象上传失败: {bucket}/{key}")
                raise Exception("上传失败")
            
            return object_url
            
        except Exception as e:
            self.logger.error(f"上传对象时出错: {bucket}/{key}, 错误: {str(e)}")
            raise
    
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
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not bucket:
                raise ValueError("存储桶名称不能为空")
            
            if not key:
                raise ValueError("对象键不能为空")
            
            # 检查对象是否存在
            if not await self.object_exists(bucket, key):
                self.logger.warning(f"对象不存在: {bucket}/{key}")
                return None
            
            self.logger.debug(f"下载对象: {bucket}/{key}")
            
            # 执行具体的下载逻辑
            data = await self._do_download_object(bucket, key)
            
            if data:
                self.logger.debug(f"对象下载成功: {bucket}/{key}, 大小: {len(data)} bytes")
            else:
                self.logger.warning(f"对象下载失败: {bucket}/{key}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"下载对象时出错: {bucket}/{key}, 错误: {str(e)}")
            return None
    
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
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not bucket:
                raise ValueError("存储桶名称不能为空")
            
            if not key:
                raise ValueError("对象键不能为空")
            
            # 检查对象是否存在
            if not await self.object_exists(bucket, key):
                self.logger.warning(f"对象不存在，无需删除: {bucket}/{key}")
                return True
            
            self.logger.info(f"删除对象: {bucket}/{key}")
            
            # 执行具体的删除逻辑
            success = await self._do_delete_object(bucket, key)
            
            if success:
                self.logger.info(f"对象删除成功: {bucket}/{key}")
            else:
                self.logger.error(f"对象删除失败: {bucket}/{key}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除对象时出错: {bucket}/{key}, 错误: {str(e)}")
            return False
    
    async def get_object_url(self,
                           bucket: str,
                           key: str,
                           expires: int = 3600) -> str:
        """
        获取对象访问URL
        
        参数:
            bucket: 存储桶名称
            key: 对象键
            expires: 过期时间（秒）
            
        返回:
            对象访问URL
        """
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not bucket:
                raise ValueError("存储桶名称不能为空")
            
            if not key:
                raise ValueError("对象键不能为空")
            
            if expires <= 0:
                raise ValueError(f"过期时间必须大于0: {expires}")
            
            # 检查对象是否存在
            if not await self.object_exists(bucket, key):
                raise ValueError(f"对象不存在: {bucket}/{key}")
            
            self.logger.debug(f"获取对象URL: {bucket}/{key}, 过期时间: {expires}s")
            
            # 执行具体的获取URL逻辑
            url = await self._do_get_object_url(bucket, key, expires)
            
            if url:
                self.logger.debug(f"对象URL获取成功: {bucket}/{key}")
            else:
                raise Exception("获取URL失败")
            
            return url
            
        except Exception as e:
            self.logger.error(f"获取对象URL时出错: {bucket}/{key}, 错误: {str(e)}")
            raise
    
    async def list_objects(self,
                         bucket: str,
                         prefix: Optional[str] = None,
                         max_keys: int = 1000) -> List[Dict[str, Any]]:
        """
        列出对象
        
        参数:
            bucket: 存储桶名称
            prefix: 对象键前缀
            max_keys: 最大返回数量
            
        返回:
            对象信息列表
        """
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not bucket:
                raise ValueError("存储桶名称不能为空")
            
            if max_keys <= 0:
                raise ValueError(f"最大返回数量必须大于0: {max_keys}")
            
            # 检查存储桶是否存在
            if not await self.bucket_exists(bucket):
                self.logger.warning(f"存储桶不存在: {bucket}")
                return []
            
            self.logger.debug(f"列出对象: {bucket}, 前缀: {prefix}, 最大数量: {max_keys}")
            
            # 执行具体的列出对象逻辑
            objects = await self._do_list_objects(bucket, prefix, max_keys)
            
            self.logger.debug(f"对象列出完成: {bucket}, 返回 {len(objects)} 个对象")
            
            return objects
            
        except Exception as e:
            self.logger.error(f"列出对象时出错: {bucket}, 错误: {str(e)}")
            return []
    
    async def object_exists(self, bucket: str, key: str) -> bool:
        """
        检查对象是否存在
        
        参数:
            bucket: 存储桶名称
            key: 对象键
            
        返回:
            对象是否存在
        """
        try:
            if not self._connected:
                await self.connect()
            
            return await self._do_object_exists(bucket, key)
            
        except Exception as e:
            self.logger.error(f"检查对象存在性时出错: {bucket}/{key}, 错误: {str(e)}")
            return False
    
    async def bucket_exists(self, bucket: str) -> bool:
        """
        检查存储桶是否存在
        
        参数:
            bucket: 存储桶名称
            
        返回:
            存储桶是否存在
        """
        try:
            if not self._connected:
                await self.connect()
            
            return await self._do_bucket_exists(bucket)
            
        except Exception as e:
            self.logger.error(f"检查存储桶存在性时出错: {bucket}, 错误: {str(e)}")
            return False
    
    async def create_bucket(self, bucket: str, **kwargs) -> bool:
        """
        创建存储桶
        
        参数:
            bucket: 存储桶名称
            **kwargs: 其他参数如区域、权限等
            
        返回:
            是否创建成功
        """
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not bucket:
                raise ValueError("存储桶名称不能为空")
            
            # 检查存储桶是否已存在
            if await self.bucket_exists(bucket):
                self.logger.warning(f"存储桶已存在: {bucket}")
                return True
            
            self.logger.info(f"创建存储桶: {bucket}")
            
            # 执行具体的创建逻辑
            success = await self._do_create_bucket(bucket, **kwargs)
            
            if success:
                self._buckets.add(bucket)
                self.logger.info(f"存储桶创建成功: {bucket}")
            else:
                self.logger.error(f"存储桶创建失败: {bucket}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"创建存储桶时出错: {bucket}, 错误: {str(e)}")
            return False
    
    async def delete_bucket(self, bucket: str, force: bool = False) -> bool:
        """
        删除存储桶
        
        参数:
            bucket: 存储桶名称
            force: 是否强制删除（删除所有对象）
            
        返回:
            是否删除成功
        """
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not bucket:
                raise ValueError("存储桶名称不能为空")
            
            # 检查存储桶是否存在
            if not await self.bucket_exists(bucket):
                self.logger.warning(f"存储桶不存在，无需删除: {bucket}")
                return True
            
            self.logger.info(f"删除存储桶: {bucket}, 强制删除: {force}")
            
            # 如果强制删除，先删除所有对象
            if force:
                objects = await self.list_objects(bucket)
                for obj in objects:
                    await self.delete_object(bucket, obj['key'])
            
            # 执行具体的删除逻辑
            success = await self._do_delete_bucket(bucket)
            
            if success:
                # 从本地缓存中移除
                self._buckets.discard(bucket)
                self.logger.info(f"存储桶删除成功: {bucket}")
            else:
                self.logger.error(f"存储桶删除失败: {bucket}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除存储桶时出错: {bucket}, 错误: {str(e)}")
            return False
    
    async def get_object_info(self, bucket: str, key: str) -> Optional[Dict[str, Any]]:
        """
        获取对象详细信息
        
        参数:
            bucket: 存储桶名称
            key: 对象键
            
        返回:
            对象信息字典
        """
        try:
            if not await self.object_exists(bucket, key):
                return None
            
            return await self._do_get_object_info(bucket, key)
            
        except Exception as e:
            self.logger.error(f"获取对象信息时出错: {bucket}/{key}, 错误: {str(e)}")
            return None
    
    async def copy_object(self, source_bucket: str, source_key: str,
                        dest_bucket: str, dest_key: str) -> bool:
        """
        复制对象
        
        参数:
            source_bucket: 源存储桶
            source_key: 源对象键
            dest_bucket: 目标存储桶
            dest_key: 目标对象键
            
        返回:
            是否复制成功
        """
        try:
            if not self._connected:
                await self.connect()
            
            # 验证参数
            if not await self.object_exists(source_bucket, source_key):
                raise ValueError(f"源对象不存在: {source_bucket}/{source_key}")
            
            # 确保目标存储桶存在
            if not await self.bucket_exists(dest_bucket):
                await self.create_bucket(dest_bucket)
            
            self.logger.info(f"复制对象: {source_bucket}/{source_key} -> {dest_bucket}/{dest_key}")
            
            # 执行具体的复制逻辑
            success = await self._do_copy_object(source_bucket, source_key, dest_bucket, dest_key)
            
            if success:
                self.logger.info(f"对象复制成功: {dest_bucket}/{dest_key}")
            else:
                self.logger.error(f"对象复制失败: {dest_bucket}/{dest_key}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"复制对象时出错: {source_bucket}/{source_key} -> {dest_bucket}/{dest_key}, 错误: {str(e)}")
            return False
    
    # ========== 抽象方法，子类必须实现 ==========
    
    @abstractmethod
    async def _do_upload_object(self, bucket: str, key: str, data: Union[bytes, BinaryIO],
                              content_type: Optional[str], metadata: Optional[Dict[str, str]]) -> str:
        """执行具体的上传对象逻辑"""
        pass
    
    @abstractmethod
    async def _do_download_object(self, bucket: str, key: str) -> Optional[bytes]:
        """执行具体的下载对象逻辑"""
        pass
    
    @abstractmethod
    async def _do_delete_object(self, bucket: str, key: str) -> bool:
        """执行具体的删除对象逻辑"""
        pass
    
    @abstractmethod
    async def _do_get_object_url(self, bucket: str, key: str, expires: int) -> str:
        """执行具体的获取对象URL逻辑"""
        pass
    
    @abstractmethod
    async def _do_list_objects(self, bucket: str, prefix: Optional[str], max_keys: int) -> List[Dict[str, Any]]:
        """执行具体的列出对象逻辑"""
        pass
    
    @abstractmethod
    async def _do_object_exists(self, bucket: str, key: str) -> bool:
        """执行具体的检查对象存在性逻辑"""
        pass
    
    @abstractmethod
    async def _do_bucket_exists(self, bucket: str) -> bool:
        """执行具体的检查存储桶存在性逻辑"""
        pass
    
    @abstractmethod
    async def _do_create_bucket(self, bucket: str, **kwargs) -> bool:
        """执行具体的创建存储桶逻辑"""
        pass
    
    @abstractmethod
    async def _do_delete_bucket(self, bucket: str) -> bool:
        """执行具体的删除存储桶逻辑"""
        pass
    
    @abstractmethod
    async def _do_get_object_info(self, bucket: str, key: str) -> Dict[str, Any]:
        """执行具体的获取对象信息逻辑"""
        pass
    
    @abstractmethod
    async def _do_copy_object(self, source_bucket: str, source_key: str,
                            dest_bucket: str, dest_key: str) -> bool:
        """执行具体的复制对象逻辑"""
        pass 