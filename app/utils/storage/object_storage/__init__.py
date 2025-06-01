"""
对象存储模块
提供对象存储和文件管理功能
"""

from .store import ObjectStore, get_object_store, create_object_store
from .minio_adapter import MinioObjectStore
from .legacy_support import (
    get_minio_client, init_minio, upload_file, download_file, 
    delete_file, get_file_url
)

__all__ = [
    # 新接口
    "ObjectStore",
    "get_object_store",
    "create_object_store", 
    "MinioObjectStore",
    
    # 向后兼容接口
    "get_minio_client",
    "init_minio",
    "upload_file",
    "download_file",
    "delete_file",
    "get_file_url"
] 