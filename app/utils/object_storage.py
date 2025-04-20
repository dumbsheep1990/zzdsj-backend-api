from typing import BinaryIO, Optional
import os
from minio import Minio
from minio.error import S3Error
from app.config import settings

# Initialize MinIO client
def get_minio_client():
    """Get MinIO client instance"""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE
    )

def init_minio():
    """Initialize MinIO bucket if it doesn't exist"""
    client = get_minio_client()
    
    # Check if bucket exists
    if not client.bucket_exists(settings.MINIO_BUCKET):
        # Create bucket
        client.make_bucket(settings.MINIO_BUCKET)
        
        # Set public read policy if needed
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
    Upload a file to MinIO storage
    Returns the object URL
    """
    client = get_minio_client()
    
    try:
        # Get file size
        file_data.seek(0, os.SEEK_END)
        file_size = file_data.tell()
        file_data.seek(0)
        
        # Upload file
        client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=file_data,
            length=file_size,
            content_type=content_type
        )
        
        # Return object URL
        return f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{object_name}"
    
    except S3Error as e:
        print(f"Error uploading file to MinIO: {e}")
        raise

def download_file(object_name: str, file_path: Optional[str] = None) -> Optional[bytes]:
    """
    Download a file from MinIO storage
    If file_path is provided, save the file there
    Otherwise, return the file data as bytes
    """
    client = get_minio_client()
    
    try:
        if file_path:
            # Save file to disk
            client.fget_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                file_path=file_path
            )
            return None
        else:
            # Return file data
            response = client.get_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name
            )
            return response.read()
    
    except S3Error as e:
        print(f"Error downloading file from MinIO: {e}")
        return None

def delete_file(object_name: str) -> bool:
    """Delete a file from MinIO storage"""
    client = get_minio_client()
    
    try:
        client.remove_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name
        )
        return True
    
    except S3Error as e:
        print(f"Error deleting file from MinIO: {e}")
        return False

def get_file_url(object_name: str, expires: int = 3600) -> str:
    """Get a presigned URL for an object"""
    client = get_minio_client()
    
    try:
        return client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=expires
        )
    
    except S3Error as e:
        print(f"Error getting presigned URL: {e}")
        raise
