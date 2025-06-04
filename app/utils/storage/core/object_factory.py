"""
对象存储工厂类
统一创建和管理不同类型的对象存储实例
"""

import logging
from typing import Dict, Any, Optional, Type, List
from enum import Enum
from datetime import datetime

from .base import ObjectStorage

logger = logging.getLogger(__name__)


class ObjectBackendType(Enum):
    """对象存储后端类型"""
    MINIO = "minio"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    ALIYUN_OSS = "aliyun_oss"


class ObjectStorageFactory:
    """对象存储工厂类"""
    
    _registry: Dict[ObjectBackendType, Type[ObjectStorage]] = {}
    _instances: Dict[str, ObjectStorage] = {}
    
    @classmethod
    def create_object_store(cls, 
                          backend_type: ObjectBackendType,
                          name: str = "default",
                          config: Optional[Dict[str, Any]] = None) -> ObjectStorage:
        """
        创建对象存储实例
        
        参数:
            backend_type: 后端类型
            name: 实例名称
            config: 配置参数
            
        返回:
            对象存储实例
        """
        try:
            # 检查是否已存在同名实例
            instance_key = f"{backend_type.value}_{name}"
            if instance_key in cls._instances:
                logger.debug(f"返回已存在的对象存储实例: {instance_key}")
                return cls._instances[instance_key]
            
            # 获取对应的类
            if backend_type not in cls._registry:
                raise ValueError(f"不支持的对象存储后端类型: {backend_type}")
            
            storage_class = cls._registry[backend_type]
            
            # 创建实例
            instance = storage_class(name=name, config=config or {})
            
            # 缓存实例
            cls._instances[instance_key] = instance
            
            logger.info(f"创建对象存储实例: {backend_type.value}, 名称: {name}")
            
            return instance
            
        except Exception as e:
            logger.error(f"创建对象存储实例失败: {backend_type}, 错误: {str(e)}")
            raise
    
    @classmethod
    def create_document_store(cls,
                            backend_type: ObjectBackendType = ObjectBackendType.MINIO,
                            config: Optional[Dict[str, Any]] = None) -> ObjectStorage:
        """
        创建专用于文档存储的对象存储实例
        
        参数:
            backend_type: 后端类型，默认MinIO
            config: 配置参数
            
        返回:
            对象存储实例
        """
        # 文档存储专用配置
        doc_config = {
            "default_bucket": "documents",
            "auto_create_bucket": True,
            "upload_timeout": 300,
            "download_timeout": 120,
            "max_file_size": 100 * 1024 * 1024,  # 100MB
        }
        
        # 合并用户配置
        if config:
            doc_config.update(config)
        
        return cls.create_object_store(
            backend_type=backend_type,
            name="document_storage",
            config=doc_config
        )
    
    @classmethod
    def create_media_store(cls,
                         backend_type: ObjectBackendType = ObjectBackendType.MINIO,
                         config: Optional[Dict[str, Any]] = None) -> ObjectStorage:
        """
        创建专用于媒体文件存储的对象存储实例
        
        参数:
            backend_type: 后端类型，默认MinIO
            config: 配置参数
            
        返回:
            对象存储实例
        """
        # 媒体存储专用配置
        media_config = {
            "default_bucket": "media",
            "auto_create_bucket": True,
            "upload_timeout": 600,  # 更长的上传超时时间
            "download_timeout": 300,
            "max_file_size": 500 * 1024 * 1024,  # 500MB
            "allowed_types": ["image/*", "audio/*", "video/*"],
        }
        
        # 合并用户配置
        if config:
            media_config.update(config)
        
        return cls.create_object_store(
            backend_type=backend_type,
            name="media_storage",
            config=media_config
        )
    
    @classmethod
    def get_instance(cls, backend_type: ObjectBackendType, name: str = "default") -> Optional[ObjectStorage]:
        """
        获取已存在的对象存储实例
        
        参数:
            backend_type: 后端类型
            name: 实例名称
            
        返回:
            对象存储实例或None
        """
        instance_key = f"{backend_type.value}_{name}"
        return cls._instances.get(instance_key)
    
    @classmethod
    def list_instances(cls) -> Dict[str, ObjectStorage]:
        """
        列出所有对象存储实例
        
        返回:
            实例字典
        """
        return cls._instances.copy()
    
    @classmethod
    def remove_instance(cls, backend_type: ObjectBackendType, name: str = "default") -> bool:
        """
        移除对象存储实例
        
        参数:
            backend_type: 后端类型
            name: 实例名称
            
        返回:
            是否成功移除
        """
        instance_key = f"{backend_type.value}_{name}"
        if instance_key in cls._instances:
            instance = cls._instances[instance_key]
            # 断开连接
            try:
                import asyncio
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(instance.disconnect())
                else:
                    asyncio.run(instance.disconnect())
            except Exception as e:
                logger.warning(f"断开对象存储连接时出错: {str(e)}")
            
            # 从缓存中移除
            del cls._instances[instance_key]
            logger.info(f"移除对象存储实例: {instance_key}")
            return True
        
        return False
    
    @classmethod
    def register_backend(cls, backend_type: ObjectBackendType, storage_class: Type[ObjectStorage]) -> None:
        """
        注册新的对象存储后端
        
        参数:
            backend_type: 后端类型
            storage_class: 存储类
        """
        cls._registry[backend_type] = storage_class
        logger.info(f"注册对象存储后端: {backend_type.value}")
    
    @classmethod
    async def shutdown_all(cls) -> None:
        """
        关闭所有对象存储实例
        """
        logger.info("开始关闭所有对象存储实例")
        
        for instance_key, instance in cls._instances.items():
            try:
                await instance.disconnect()
                logger.debug(f"已关闭对象存储实例: {instance_key}")
            except Exception as e:
                logger.error(f"关闭对象存储实例失败: {instance_key}, 错误: {str(e)}")
        
        cls._instances.clear()
        logger.info("所有对象存储实例已关闭")


class DocumentObjectManager:
    """
    文档对象管理器
    专门处理文档相关的对象存储操作
    """
    
    def __init__(self, object_store: ObjectStorage):
        """
        初始化文档对象管理器
        
        参数:
            object_store: 对象存储实例
        """
        self.object_store = object_store
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    async def upload_document(self, 
                            document_id: str,
                            file_name: str,
                            file_data: bytes,
                            content_type: Optional[str] = None,
                            metadata: Optional[Dict[str, str]] = None) -> str:
        """
        上传文档文件
        
        参数:
            document_id: 文档ID
            file_name: 文件名
            file_data: 文件数据
            content_type: 内容类型
            metadata: 元数据
            
        返回:
            文件URL
        """
        try:
            # 构建对象键
            object_key = f"documents/{document_id}/{file_name}"
            
            # 准备元数据
            doc_metadata = {
                "document_id": document_id,
                "original_filename": file_name,
                "upload_time": str(datetime.now()),
            }
            if metadata:
                doc_metadata.update(metadata)
            
            # 上传文件
            url = await self.object_store.upload_object(
                bucket="documents",
                key=object_key,
                data=file_data,
                content_type=content_type,
                metadata=doc_metadata
            )
            
            self.logger.info(f"文档上传成功: {document_id}/{file_name}")
            return url
            
        except Exception as e:
            self.logger.error(f"文档上传失败: {document_id}/{file_name}, 错误: {str(e)}")
            raise
    
    async def download_document(self, document_id: str, file_name: str) -> Optional[bytes]:
        """
        下载文档文件
        
        参数:
            document_id: 文档ID
            file_name: 文件名
            
        返回:
            文件数据
        """
        try:
            object_key = f"documents/{document_id}/{file_name}"
            
            data = await self.object_store.download_object(
                bucket="documents",
                key=object_key
            )
            
            if data:
                self.logger.debug(f"文档下载成功: {document_id}/{file_name}")
            else:
                self.logger.warning(f"文档下载失败: {document_id}/{file_name}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"文档下载失败: {document_id}/{file_name}, 错误: {str(e)}")
            return None
    
    async def delete_document(self, document_id: str, file_name: str) -> bool:
        """
        删除文档文件
        
        参数:
            document_id: 文档ID
            file_name: 文件名
            
        返回:
            是否删除成功
        """
        try:
            object_key = f"documents/{document_id}/{file_name}"
            
            success = await self.object_store.delete_object(
                bucket="documents",
                key=object_key
            )
            
            if success:
                self.logger.info(f"文档删除成功: {document_id}/{file_name}")
            else:
                self.logger.warning(f"文档删除失败: {document_id}/{file_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"文档删除失败: {document_id}/{file_name}, 错误: {str(e)}")
            return False
    
    async def list_document_files(self, document_id: str) -> List[Dict[str, Any]]:
        """
        列出文档的所有文件
        
        参数:
            document_id: 文档ID
            
        返回:
            文件信息列表
        """
        try:
            prefix = f"documents/{document_id}/"
            
            objects = await self.object_store.list_objects(
                bucket="documents",
                prefix=prefix
            )
            
            # 处理文件信息
            files = []
            for obj in objects:
                # 提取文件名（移除前缀）
                file_name = obj['key'][len(prefix):]
                if file_name:  # 忽略目录本身
                    files.append({
                        "file_name": file_name,
                        "size": obj.get("size", 0),
                        "last_modified": obj.get("last_modified"),
                        "content_type": obj.get("content_type"),
                        "url": obj.get("url")
                    })
            
            self.logger.debug(f"列出文档文件: {document_id}, 文件数: {len(files)}")
            return files
            
        except Exception as e:
            self.logger.error(f"列出文档文件失败: {document_id}, 错误: {str(e)}")
            return []
    
    async def get_document_file_url(self, document_id: str, file_name: str, expires: int = 3600) -> Optional[str]:
        """
        获取文档文件的访问URL
        
        参数:
            document_id: 文档ID
            file_name: 文件名
            expires: 过期时间（秒）
            
        返回:
            文件访问URL
        """
        try:
            object_key = f"documents/{document_id}/{file_name}"
            
            url = await self.object_store.get_object_url(
                bucket="documents",
                key=object_key,
                expires=expires
            )
            
            self.logger.debug(f"获取文档文件URL: {document_id}/{file_name}")
            return url
            
        except Exception as e:
            self.logger.error(f"获取文档文件URL失败: {document_id}/{file_name}, 错误: {str(e)}")
            return None 