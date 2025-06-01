from typing import BinaryIO, Optional
import os
from minio import Minio
from minio.error import S3Error
from app.config import settings

# 初始化MinIO客户端
def get_minio_client():
    """获取MinIO客户端实例"""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )

def init_minio():
    """如果不存在则初始化MinIO存储桶"""
    client = get_minio_client()
    
    # 检查存储桶是否存在
    if not client.bucket_exists(settings.MINIO_BUCKET):
        # 创建存储桶
        client.make_bucket(settings.MINIO_BUCKET)
        
        # 如果需要设置公共读取策略
        # policy = {
        #     "Version": "2012-10-17",
        #     "Statement": [
        #         {
        #             "Effect": "Allow",
        #             "Principal": {"AWS": "*"},
        #             "Action": ["s3:GetObject"],
        #             "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"]
        #         }
        #     ]
        # }
        # client.set_bucket_policy(settings.MINIO_BUCKET, json.dumps(policy))

def upload_file(file_data: BinaryIO, object_name: str, content_type: Optional[str] = None) -> str:
    """
    上传文件到MinIO存储
    返回对象URL
    """
    client = get_minio_client()
    
    try:
        # 获取文件大小
        file_data.seek(0, os.SEEK_END)
        file_size = file_data.tell()
        file_data.seek(0)
        
        # 上传文件
        client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=file_data,
            length=file_size,
            content_type=content_type
        )
        
        # 返回对象URL
        return f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{object_name}"
    
    except S3Error as e:
        print(f"向MinIO上传文件时出错: {e}")
        raise

def download_file(object_name: str, file_path: Optional[str] = None) -> Optional[bytes]:
    """
    从MinIO存储下载文件
    如果提供了file_path，则将文件保存到该位置
    否则，将文件数据作为字节返回
    """
    client = get_minio_client()
    
    try:
        if file_path:
            # 将文件保存到磁盘
            client.fget_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                file_path=file_path
            )
            return None
        else:
            # 返回文件数据
            response = client.get_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name
            )
            return response.read()
    
    except S3Error as e:
        print(f"从MinIO下载文件时出错: {e}")
        return None

def delete_file(object_name: str) -> bool:
    """从MinIO存储删除文件"""
    client = get_minio_client()
    
    try:
        client.remove_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name
        )
        return True
    
    except S3Error as e:
        print(f"从MinIO删除文件时出错: {e}")
        return False

def get_file_url(object_name: str, expires: int = 3600) -> str:
    """获取对象的预签名URL"""
    client = get_minio_client()
    
    try:
        return client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=expires
        )
    
    except S3Error as e:
        print(f"获取预签名URL时出错: {e}")
        raise
