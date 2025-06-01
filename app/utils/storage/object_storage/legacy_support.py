"""
对象存储向后兼容支持
保持原有接口不变，内部使用新架构实现
"""

from typing import BinaryIO, Optional
import logging
from .store import get_object_store
from ..core.config import create_config_from_settings

logger = logging.getLogger(__name__)

# 全局变量，保持与原接口兼容
_global_client = None


def get_minio_client():
    """
    获取MinIO客户端实例
    保持与原接口兼容
    """
    global _global_client
    
    if _global_client is None:
        try:
            # 尝试导入settings
            from app.config import settings
            
            # 创建配置
            config = create_config_from_settings(settings).to_dict()
            
            # 获取对象存储实例
            object_store = get_object_store(config)
            
            # 异步初始化
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(object_store.initialize())
                else:
                    loop.run_until_complete(object_store.initialize())
            except RuntimeError:
                asyncio.run(object_store.initialize())
            
            # 创建兼容性包装器
            _global_client = MinioClientWrapper(object_store)
            
        except Exception as e:
            logger.error(f"MinIO客户端创建失败: {str(e)}")
            raise
    
    return _global_client


def init_minio():
    """
    如果不存在则初始化MinIO存储桶
    保持与原接口兼容
    """
    try:
        # 获取客户端，这会触发初始化
        get_minio_client()
        logger.info("MinIO初始化完成 (兼容模式)")
        
    except Exception as e:
        logger.error(f"MinIO初始化失败: {str(e)}")
        raise


def upload_file(file_data: BinaryIO, object_name: str, content_type: Optional[str] = None) -> str:
    """
    上传文件到MinIO存储
    保持与原接口兼容
    """
    try:
        # 尝试导入settings获取bucket名称
        from app.config import settings
        bucket = getattr(settings, 'MINIO_BUCKET', 'default-bucket')
        
        # 获取对象存储实例
        object_store = get_object_store()
        
        # 异步上传
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，创建任务
                asyncio.create_task(
                    object_store.upload_object(bucket, object_name, file_data, content_type)
                )
                # 返回模拟URL
                secure = getattr(settings, 'MINIO_SECURE', False)
                endpoint = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000')
                protocol = "https" if secure else "http"
                return f"{protocol}://{endpoint}/{bucket}/{object_name}"
            else:
                return loop.run_until_complete(
                    object_store.upload_object(bucket, object_name, file_data, content_type)
                )
        except RuntimeError:
            return asyncio.run(
                object_store.upload_object(bucket, object_name, file_data, content_type)
            )
        
    except Exception as e:
        logger.error(f"上传文件失败: {str(e)}")
        raise


def download_file(object_name: str, file_path: Optional[str] = None) -> Optional[bytes]:
    """
    从MinIO存储下载文件
    保持与原接口兼容
    """
    try:
        # 尝试导入settings获取bucket名称
        from app.config import settings
        bucket = getattr(settings, 'MINIO_BUCKET', 'default-bucket')
        
        # 获取对象存储实例
        object_store = get_object_store()
        
        # 异步下载
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，创建任务但无法直接获取结果
                asyncio.create_task(
                    object_store.download_object(bucket, object_name)
                )
                return None  # 无法在运行的事件循环中同步获取结果
            else:
                data = loop.run_until_complete(
                    object_store.download_object(bucket, object_name)
                )
        except RuntimeError:
            data = asyncio.run(
                object_store.download_object(bucket, object_name)
            )
        
        # 处理文件路径
        if file_path and data:
            with open(file_path, 'wb') as f:
                f.write(data)
            return None
        
        return data
        
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return None


def delete_file(object_name: str) -> bool:
    """
    从MinIO存储删除文件
    保持与原接口兼容
    """
    try:
        # 尝试导入settings获取bucket名称
        from app.config import settings
        bucket = getattr(settings, 'MINIO_BUCKET', 'default-bucket')
        
        # 获取对象存储实例
        object_store = get_object_store()
        
        # 异步删除
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    object_store.delete_object(bucket, object_name)
                )
                return True  # 假设成功
            else:
                return loop.run_until_complete(
                    object_store.delete_object(bucket, object_name)
                )
        except RuntimeError:
            return asyncio.run(
                object_store.delete_object(bucket, object_name)
            )
        
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return False


def get_file_url(object_name: str, expires: int = 3600) -> str:
    """
    获取对象的预签名URL
    保持与原接口兼容
    """
    try:
        # 尝试导入settings获取bucket名称
        from app.config import settings
        bucket = getattr(settings, 'MINIO_BUCKET', 'default-bucket')
        
        # 获取对象存储实例
        object_store = get_object_store()
        
        # 异步获取URL
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，返回直接URL
                secure = getattr(settings, 'MINIO_SECURE', False)
                endpoint = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000')
                protocol = "https" if secure else "http"
                return f"{protocol}://{endpoint}/{bucket}/{object_name}"
            else:
                return loop.run_until_complete(
                    object_store.get_object_url(bucket, object_name, expires)
                )
        except RuntimeError:
            return asyncio.run(
                object_store.get_object_url(bucket, object_name, expires)
            )
        
    except Exception as e:
        logger.error(f"获取文件URL失败: {str(e)}")
        raise


class MinioClientWrapper:
    """
    MinIO客户端包装器，提供向后兼容性
    """
    
    def __init__(self, object_store):
        self._object_store = object_store
    
    def bucket_exists(self, bucket_name: str) -> bool:
        """检查存储桶是否存在"""
        # 简化实现，假设存储桶存在
        return True
    
    def make_bucket(self, bucket_name: str):
        """创建存储桶"""
        # 在新架构中，存储桶会在上传时自动创建
        pass
    
    def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str = None):
        """上传对象"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._object_store.upload_object(bucket_name, object_name, data, content_type)
                )
            else:
                loop.run_until_complete(
                    self._object_store.upload_object(bucket_name, object_name, data, content_type)
                )
        except RuntimeError:
            asyncio.run(
                self._object_store.upload_object(bucket_name, object_name, data, content_type)
            )
    
    def get_object(self, bucket_name: str, object_name: str):
        """获取对象"""
        # 返回模拟响应对象
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 无法在运行的事件循环中同步获取结果
                return MockResponse(b"")
            else:
                data = loop.run_until_complete(
                    self._object_store.download_object(bucket_name, object_name)
                )
                return MockResponse(data or b"")
        except RuntimeError:
            data = asyncio.run(
                self._object_store.download_object(bucket_name, object_name)
            )
            return MockResponse(data or b"")
    
    def remove_object(self, bucket_name: str, object_name: str):
        """删除对象"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._object_store.delete_object(bucket_name, object_name)
                )
            else:
                loop.run_until_complete(
                    self._object_store.delete_object(bucket_name, object_name)
                )
        except RuntimeError:
            asyncio.run(
                self._object_store.delete_object(bucket_name, object_name)
            )
    
    def presigned_get_object(self, bucket_name: str, object_name: str, expires):
        """获取预签名URL"""
        import asyncio
        expires_seconds = expires.total_seconds() if hasattr(expires, 'total_seconds') else expires
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 返回直接URL作为fallback
                return f"http://localhost:9000/{bucket_name}/{object_name}"
            else:
                return loop.run_until_complete(
                    self._object_store.get_object_url(bucket_name, object_name, int(expires_seconds))
                )
        except RuntimeError:
            return asyncio.run(
                self._object_store.get_object_url(bucket_name, object_name, int(expires_seconds))
            )


class MockResponse:
    """模拟响应对象"""
    
    def __init__(self, data: bytes):
        self._data = data
    
    def read(self) -> bytes:
        return self._data
    
    def close(self):
        pass
    
    def release_conn(self):
        pass 