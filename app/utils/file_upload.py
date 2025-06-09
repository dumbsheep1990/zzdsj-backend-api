"""
文件上传助手模块
提供统一的文件上传接口，支持MinIO对象存储
确保文件上传与文档处理流程的集成
"""

import os
import uuid
import logging
import hashlib
from typing import Optional, Dict, Any, BinaryIO, Tuple, List
from fastapi import UploadFile, HTTPException
from datetime import datetime
import mimetypes

from app.config import settings
from app.utils.storage.object_storage import init_minio, upload_file, get_file_url

logger = logging.getLogger(__name__)

class FileUploadManager:
    """文件上传管理器"""
    
    # 支持的文件类型
    SUPPORTED_DOCUMENT_TYPES = {
        'text/plain': ['.txt'],
        'application/pdf': ['.pdf'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'application/msword': ['.doc'],
        'text/markdown': ['.md', '.markdown'],
        'text/html': ['.html', '.htm'],
        'application/rtf': ['.rtf'],
        'text/csv': ['.csv'],
        'application/json': ['.json'],
        'application/xml': ['.xml'],
        'text/xml': ['.xml']
    }
    
    SUPPORTED_IMAGE_TYPES = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/bmp': ['.bmp'],
        'image/webp': ['.webp'],
        'image/svg+xml': ['.svg']
    }
    
    SUPPORTED_AUDIO_TYPES = {
        'audio/mpeg': ['.mp3'],
        'audio/wav': ['.wav'],
        'audio/x-m4a': ['.m4a'],
        'audio/ogg': ['.ogg'],
        'audio/flac': ['.flac']
    }
    
    SUPPORTED_VIDEO_TYPES = {
        'video/mp4': ['.mp4'],
        'video/avi': ['.avi'],
        'video/mkv': ['.mkv'],
        'video/mov': ['.mov'],
        'video/wmv': ['.wmv'],
        'video/webm': ['.webm']
    }
    
    # 文件大小限制 (MB)
    MAX_FILE_SIZES = {
        'document': 50,  # 50MB
        'image': 10,     # 10MB
        'audio': 100,    # 100MB
        'video': 500     # 500MB
    }
    
    def __init__(self):
        """初始化文件上传管理器"""
        self.initialized = False
        self._ensure_minio_initialized()
    
    def _ensure_minio_initialized(self):
        """确保MinIO已初始化"""
        if not self.initialized:
            try:
                init_minio()
                self.initialized = True
                logger.info("MinIO文件上传管理器初始化成功")
            except Exception as e:
                logger.error(f"MinIO初始化失败: {e}")
                raise
    
    def validate_file(self, file: UploadFile) -> Tuple[bool, str, str]:
        """
        验证上传文件
        
        Args:
            file: 上传的文件对象
            
        Returns:
            Tuple[bool, str, str]: (是否有效, 文件类型, 错误信息)
        """
        # 检查文件名
        if not file.filename:
            return False, "", "文件名不能为空"
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file.filename.lower())[1]
        if not file_ext:
            return False, "", "文件必须有扩展名"
        
        # 检查文件类型
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        if not content_type:
            return False, "", "无法确定文件类型"
        
        # 确定文件类别
        file_category = self._get_file_category(content_type, file_ext)
        if not file_category:
            return False, "", f"不支持的文件类型: {content_type}"
        
        # 检查文件大小
        if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
            current_pos = file.file.tell()
            file.file.seek(0, 2)  # 移到文件末尾
            file_size = file.file.tell()
            file.file.seek(current_pos)  # 恢复原来位置
            
            max_size_mb = self.MAX_FILE_SIZES.get(file_category, 10)
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if file_size > max_size_bytes:
                return False, file_category, f"文件大小超过限制 ({max_size_mb}MB)"
        
        return True, file_category, ""
    
    def _get_file_category(self, content_type: str, file_ext: str) -> Optional[str]:
        """获取文件类别"""
        # 检查文档类型
        for mime_type, extensions in self.SUPPORTED_DOCUMENT_TYPES.items():
            if content_type == mime_type or file_ext in extensions:
                return "document"
        
        # 检查图片类型
        for mime_type, extensions in self.SUPPORTED_IMAGE_TYPES.items():
            if content_type == mime_type or file_ext in extensions:
                return "image"
        
        # 检查音频类型
        for mime_type, extensions in self.SUPPORTED_AUDIO_TYPES.items():
            if content_type == mime_type or file_ext in extensions:
                return "audio"
        
        # 检查视频类型
        for mime_type, extensions in self.SUPPORTED_VIDEO_TYPES.items():
            if content_type == mime_type or file_ext in extensions:
                return "video"
        
        return None
    
    def generate_file_path(self, 
                          filename: str, 
                          kb_id: str, 
                          doc_id: Optional[str] = None,
                          file_category: str = "document") -> str:
        """
        生成文件存储路径
        
        Args:
            filename: 原始文件名
            kb_id: 知识库ID
            doc_id: 文档ID (可选)
            file_category: 文件类别
            
        Returns:
            str: 文件存储路径
        """
        # 生成唯一文件名
        file_ext = os.path.splitext(filename)[1]
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{unique_id}{file_ext}"
        
        # 构建路径
        if doc_id:
            # 文档相关文件
            path = f"{file_category}s/{kb_id}/{doc_id}/{unique_filename}"
        else:
            # 知识库级别文件
            path = f"{file_category}s/{kb_id}/{unique_filename}"
        
        return path
    
    async def upload_file_to_minio(self, 
                                   file: UploadFile,
                                   kb_id: str,
                                   doc_id: Optional[str] = None,
                                   metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        上传文件到MinIO
        
        Args:
            file: 上传的文件对象
            kb_id: 知识库ID
            doc_id: 文档ID (可选)
            metadata: 额外的元数据
            
        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            # 验证文件
            is_valid, file_category, error_msg = self.validate_file(file)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            
            # 生成文件路径
            file_path = self.generate_file_path(
                file.filename, kb_id, doc_id, file_category
            )
            
            # 计算文件哈希
            file_content = await file.read()
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # 重置文件指针
            await file.seek(0)
            
            # 准备元数据
            upload_metadata = {
                "original_filename": file.filename,
                "content_type": file.content_type,
                "file_category": file_category,
                "kb_id": kb_id,
                "file_hash": file_hash,
                "upload_time": datetime.now().isoformat(),
                "file_size": str(len(file_content))
            }
            
            if doc_id:
                upload_metadata["doc_id"] = doc_id
            
            if metadata:
                upload_metadata.update(metadata)
            
            # 上传到MinIO
            file_url = upload_file(
                file_data=file.file,
                object_name=file_path,
                content_type=file.content_type
            )
            
            logger.info(f"文件上传成功: {file.filename} -> {file_path}")
            
            return {
                "success": True,
                "file_url": file_url,
                "file_path": file_path,
                "file_category": file_category,
                "file_size": len(file_content),
                "file_hash": file_hash,
                "metadata": upload_metadata
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    async def upload_multiple_files(self,
                                    files: List[UploadFile],
                                    kb_id: str,
                                    doc_id: Optional[str] = None) -> Dict[str, Any]:
        """
        批量上传文件
        
        Args:
            files: 文件列表
            kb_id: 知识库ID
            doc_id: 文档ID (可选)
            
        Returns:
            Dict[str, Any]: 批量上传结果
        """
        results = []
        success_count = 0
        error_count = 0
        
        for file in files:
            try:
                result = await self.upload_file_to_minio(file, kb_id, doc_id)
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "result": result
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": str(e)
                })
                error_count += 1
        
        return {
            "total_files": len(files),
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }
    
    def get_file_download_url(self, file_path: str, expires: int = 3600) -> str:
        """
        获取文件下载URL
        
        Args:
            file_path: 文件路径
            expires: 过期时间(秒)
            
        Returns:
            str: 下载URL
        """
        try:
            return get_file_url(file_path, expires)
        except Exception as e:
            logger.error(f"获取文件下载URL失败: {e}")
            raise HTTPException(status_code=500, detail="获取文件下载URL失败")
    
    def get_supported_types(self) -> Dict[str, List[str]]:
        """获取支持的文件类型"""
        return {
            "documents": list(self.SUPPORTED_DOCUMENT_TYPES.keys()),
            "images": list(self.SUPPORTED_IMAGE_TYPES.keys()),
            "audios": list(self.SUPPORTED_AUDIO_TYPES.keys()),
            "videos": list(self.SUPPORTED_VIDEO_TYPES.keys())
        }
    
    def get_max_file_sizes(self) -> Dict[str, int]:
        """获取最大文件大小限制(MB)"""
        return self.MAX_FILE_SIZES.copy()


# 全局文件上传管理器实例
upload_manager = FileUploadManager()

# 向后兼容的函数接口
async def upload_file_to_minio(file: UploadFile, 
                               kb_id: str, 
                               doc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    上传文件到MinIO (向后兼容接口)
    
    Args:
        file: 上传的文件对象
        kb_id: 知识库ID 
        doc_id: 文档ID (可选)
        
    Returns:
        Dict[str, Any]: 上传结果
    """
    return await upload_manager.upload_file_to_minio(file, kb_id, doc_id)

def validate_upload_file(file: UploadFile) -> Tuple[bool, str]:
    """
    验证上传文件 (向后兼容接口)
    
    Args:
        file: 上传的文件对象
        
    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    is_valid, _, error_msg = upload_manager.validate_file(file)
    return is_valid, error_msg 