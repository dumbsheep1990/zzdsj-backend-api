"""
MinIO对象存储适配器
"""

from typing import List, Dict, Any, Optional, Union, BinaryIO
import logging
import io
import os
from ..core.base import ObjectStorage
from ..core.exceptions import ObjectStoreError, ConnectionError

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    # 提供fallback类以避免NameError
    class Minio:
        pass
    class S3Error(Exception):
        pass

logger = logging.getLogger(__name__)


class MinioObjectStore(ObjectStorage):
    """
    MinIO对象存储适配器
    实现基于MinIO的对象存储功能
    """
    
    def __init__(self, name: str = "minio", config: Optional[Dict[str, Any]] = None):
        """
        初始化MinIO对象存储
        
        参数:
            name: 存储名称
            config: 配置参数
        """
        super().__init__(name, config)
        self._client = None
    
    async def initialize(self) -> None:
        """初始化MinIO对象存储"""
        if self._initialized:
            return
        
        if not MINIO_AVAILABLE:
            raise ObjectStoreError("MinIO依赖库未安装")
        
        try:
            # 从配置获取连接参数
            endpoint = self.get_config("object_store_endpoint", "localhost:9000")
            access_key = self.get_config("object_store_access_key", "")
            secret_key = self.get_config("object_store_secret_key", "")
            secure = self.get_config("object_store_secure", False)
            
            # 创建MinIO客户端
            self._client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            
            self._initialized = True
            self._connected = True
            self.logger.info(f"MinIO初始化成功: {endpoint}")
            
        except Exception as e:
            self.logger.error(f"MinIO初始化失败: {str(e)}")
            raise ConnectionError(f"MinIO连接失败: {str(e)}", endpoint=endpoint)
    
    async def connect(self) -> bool:
        """建立连接"""
        if not self._initialized:
            await self.initialize()
        return self._connected
    
    async def disconnect(self) -> None:
        """断开连接"""
        # MinIO客户端不需要显式断开连接
        self._connected = False
        self.logger.info("MinIO连接已断开")
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._connected or not self._client or not MINIO_AVAILABLE:
                return False
            
            # 尝试列出存储桶来验证连接
            list(self._client.list_buckets())
            return True
        except Exception as e:
            self.logger.warning(f"MinIO健康检查失败: {str(e)}")
            return False
    
    async def upload_object(self,
                          bucket: str,
                          key: str,
                          data: Union[bytes, BinaryIO],
                          content_type: Optional[str] = None,
                          metadata: Optional[Dict[str, str]] = None) -> str:
        """上传对象"""
        if not MINIO_AVAILABLE:
            raise ObjectStoreError("MinIO依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 确保存储桶存在
            await self._ensure_bucket_exists(bucket)
            
            # 处理数据类型
            if isinstance(data, bytes):
                data_stream = io.BytesIO(data)
                data_length = len(data)
            else:
                # 如果是文件对象，获取长度
                current_pos = data.tell()
                data.seek(0, os.SEEK_END)
                data_length = data.tell()
                data.seek(current_pos)
                data_stream = data
            
            # 上传对象
            self._client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=data_stream,
                length=data_length,
                content_type=content_type,
                metadata=metadata
            )
            
            # 生成对象URL
            secure = self.get_config("object_store_secure", False)
            endpoint = self.get_config("object_store_endpoint", "localhost:9000")
            protocol = "https" if secure else "http"
            url = f"{protocol}://{endpoint}/{bucket}/{key}"
            
            self.logger.info(f"成功上传对象: {bucket}/{key}")
            return url
            
        except S3Error as e:
            self.logger.error(f"上传对象失败: {str(e)}")
            raise ObjectStoreError(f"上传对象失败: {str(e)}", bucket=bucket, key=key)
    
    async def download_object(self,
                            bucket: str,
                            key: str) -> Optional[bytes]:
        """下载对象"""
        if not MINIO_AVAILABLE:
            raise ObjectStoreError("MinIO依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 下载对象
            response = self._client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            
            self.logger.info(f"成功下载对象: {bucket}/{key}")
            return data
            
        except S3Error as e:
            self.logger.error(f"下载对象失败: {str(e)}")
            return None
    
    async def delete_object(self,
                          bucket: str,
                          key: str) -> bool:
        """删除对象"""
        if not MINIO_AVAILABLE:
            raise ObjectStoreError("MinIO依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 删除对象
            self._client.remove_object(bucket, key)
            
            self.logger.info(f"成功删除对象: {bucket}/{key}")
            return True
            
        except S3Error as e:
            self.logger.error(f"删除对象失败: {str(e)}")
            return False
    
    async def get_object_url(self,
                           bucket: str,
                           key: str,
                           expires: int = 3600) -> str:
        """获取对象预签名URL"""
        if not MINIO_AVAILABLE:
            raise ObjectStoreError("MinIO依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 生成预签名URL
            from datetime import timedelta
            url = self._client.presigned_get_object(
                bucket_name=bucket,
                object_name=key,
                expires=timedelta(seconds=expires)
            )
            
            return url
            
        except S3Error as e:
            self.logger.error(f"获取对象URL失败: {str(e)}")
            raise ObjectStoreError(f"获取对象URL失败: {str(e)}", bucket=bucket, key=key)
    
    async def list_objects(self,
                         bucket: str,
                         prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出对象"""
        if not MINIO_AVAILABLE:
            raise ObjectStoreError("MinIO依赖库未安装")
            
        try:
            if not self._connected:
                await self.connect()
            
            # 列出对象
            objects = self._client.list_objects(bucket, prefix=prefix, recursive=True)
            
            result = []
            for obj in objects:
                result.append({
                    "key": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "content_type": getattr(obj, 'content_type', None)
                })
            
            self.logger.info(f"成功列出对象: {bucket}, 数量: {len(result)}")
            return result
            
        except S3Error as e:
            self.logger.error(f"列出对象失败: {str(e)}")
            raise ObjectStoreError(f"列出对象失败: {str(e)}", bucket=bucket)
    
    async def _ensure_bucket_exists(self, bucket: str) -> None:
        """确保存储桶存在"""
        if not MINIO_AVAILABLE:
            raise ObjectStoreError("MinIO依赖库未安装")
            
        try:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
                self.logger.info(f"创建存储桶: {bucket}")
        except S3Error as e:
            self.logger.error(f"创建存储桶失败: {str(e)}")
            raise ObjectStoreError(f"创建存储桶失败: {str(e)}", bucket=bucket) 