#!/usr/bin/env python3
"""
统一文件上传中间件
集成文档管理器，提供标准化的文件上传处理流程
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from fastapi import UploadFile, HTTPException
from datetime import datetime

from document_manager import get_document_manager
from storage_interface import get_file_storage
from app.utils.file_upload import FileUploadManager

logger = logging.getLogger(__name__)

class UnifiedFileUploadMiddleware:
    """统一文件上传中间件"""
    
    def __init__(self):
        self.doc_manager = get_document_manager()
        self.upload_manager = FileUploadManager()
        self.storage = get_file_storage()
    
    async def upload_document(self,
                            file: UploadFile,
                            kb_id: str = None,
                            category: str = "general",
                            metadata: Dict[str, Any] = None,
                            auto_vectorize: bool = True,
                            user_id: str = None) -> Dict[str, Any]:
        """
        统一文档上传处理
        
        Args:
            file: 上传的文件
            kb_id: 知识库ID
            category: 文档分类
            metadata: 额外元数据
            auto_vectorize: 是否自动向量化
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            # 1. 文件验证
            is_valid, file_category, error_msg = self.upload_manager.validate_file(file)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            
            # 2. 准备元数据
            upload_metadata = {
                "category": category,
                "file_category": file_category,
                "auto_vectorize": auto_vectorize,
                "uploaded_at": datetime.now().isoformat()
            }
            
            if user_id:
                upload_metadata["uploaded_by"] = user_id
            
            if metadata:
                upload_metadata.update(metadata)
            
            # 3. 使用文档管理器上传
            result = await self.doc_manager.upload_document(
                file=file,
                kb_id=kb_id,
                metadata=upload_metadata
            )
            
            # 4. 添加分类信息到返回结果
            result.update({
                "file_category": file_category,
                "category": category,
                "auto_vectorize": auto_vectorize
            })
            
            logger.info(f"统一上传成功: {file.filename} -> {result['file_id']}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"统一文件上传失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    async def batch_upload_documents(self,
                                   files: List[UploadFile],
                                   kb_id: str = None,
                                   category: str = "batch_upload",
                                   auto_vectorize: bool = True,
                                   user_id: str = None) -> Dict[str, Any]:
        """
        批量文档上传处理
        
        Args:
            files: 文件列表
            kb_id: 知识库ID
            category: 文档分类
            auto_vectorize: 是否自动向量化
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 批量上传结果
        """
        try:
            # 准备文件列表
            upload_tasks = []
            for file in files:
                # 验证每个文件
                is_valid, file_category, error_msg = self.upload_manager.validate_file(file)
                if not is_valid:
                    upload_tasks.append({
                        "filename": file.filename,
                        "status": "error",
                        "error": error_msg
                    })
                    continue
                
                # 准备元数据
                metadata = {
                    "category": category,
                    "file_category": file_category,
                    "auto_vectorize": auto_vectorize,
                    "uploaded_at": datetime.now().isoformat()
                }
                
                if user_id:
                    metadata["uploaded_by"] = user_id
                
                upload_tasks.append({
                    "file": file,
                    "filename": file.filename,
                    "metadata": metadata
                })
            
            # 使用文档管理器批量上传
            result = await self.doc_manager.batch_upload_documents(
                files=upload_tasks,
                kb_id=kb_id
            )
            
            logger.info(f"批量上传完成: {result['success_count']}/{result['total_files']}")
            return result
            
        except Exception as e:
            logger.error(f"批量文件上传失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"批量文件上传失败: {str(e)}")
    
    async def upload_user_file(self,
                             file: UploadFile,
                             folder: str = "user_files",
                             user_id: str = None,
                             allowed_types: List[str] = None,
                             max_size_mb: int = 10) -> Dict[str, Any]:
        """
        用户文件上传处理（头像、附件等）
        
        Args:
            file: 上传的文件
            folder: 存储文件夹
            user_id: 用户ID
            allowed_types: 允许的文件类型
            max_size_mb: 最大文件大小(MB)
            
        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            # 1. 基本验证
            if allowed_types and file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件类型: {file.content_type}"
                )
            
            # 2. 文件大小验证
            file_content = await file.read()
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if len(file_content) > max_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"文件大小超过限制({max_size_mb}MB)"
                )
            
            # 3. 准备元数据
            metadata = {
                "folder": folder,
                "file_category": "user_file",
                "uploaded_at": datetime.now().isoformat()
            }
            
            if user_id:
                metadata["uploaded_by"] = user_id
            
            # 4. 上传到存储
            file_metadata = self.storage.upload_file(
                file_data=file_content,
                filename=file.filename,
                content_type=file.content_type,
                metadata=metadata
            )
            
            # 5. 构造返回结果
            result = {
                "success": True,
                "file_id": file_metadata.file_id,
                "filename": file_metadata.filename,
                "file_url": self._get_file_url(file_metadata),
                "file_size": file_metadata.file_size,
                "content_type": file_metadata.content_type,
                "upload_time": file_metadata.upload_time.isoformat()
            }
            
            logger.info(f"用户文件上传成功: {file.filename} -> {file_metadata.file_id}")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"用户文件上传失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"用户文件上传失败: {str(e)}")
    
    async def delete_document(self, file_id: str, force: bool = False) -> Dict[str, Any]:
        """
        删除文档（关联删除）
        
        Args:
            file_id: 文件ID
            force: 是否强制删除
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        try:
            result = await self.doc_manager.delete_document(file_id, force=force)
            logger.info(f"文档删除{'成功' if result['success'] else '失败'}: {file_id}")
            return result
            
        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")
    
    async def delete_user_file(self, file_id: str) -> Dict[str, Any]:
        """
        删除用户文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        try:
            deleted = self.storage.delete_file(file_id)
            
            result = {
                "success": deleted,
                "file_id": file_id,
                "message": "文件删除成功" if deleted else "文件删除失败"
            }
            
            logger.info(f"用户文件删除{'成功' if deleted else '失败'}: {file_id}")
            return result
            
        except Exception as e:
            logger.error(f"删除用户文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"删除用户文件失败: {str(e)}")
    
    def get_supported_types(self) -> Dict[str, Any]:
        """获取支持的文件类型"""
        return self.upload_manager.get_supported_types()
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        try:
            # 先尝试从文档管理器获取
            doc_info = self.doc_manager.get_document_info(file_id)
            if doc_info:
                return doc_info
            
            # 再尝试从存储获取
            file_metadata = self.storage.get_file_metadata(file_id)
            if file_metadata:
                return {
                    "file_id": file_metadata.file_id,
                    "filename": file_metadata.filename,
                    "content_type": file_metadata.content_type,
                    "file_size": file_metadata.file_size,
                    "file_hash": file_metadata.file_hash,
                    "upload_time": file_metadata.upload_time.isoformat(),
                    "storage_path": file_metadata.storage_path,
                    "metadata": file_metadata.metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return None
    
    def _get_file_url(self, file_metadata) -> str:
        """生成文件访问URL"""
        try:
            # 这里应该根据实际的存储配置生成URL
            # 暂时返回一个模拟URL
            from app.config import settings
            if hasattr(settings, 'MINIO_ENDPOINT'):
                protocol = "https" if getattr(settings, 'MINIO_SECURE', False) else "http"
                endpoint = getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000')
                bucket = getattr(settings, 'MINIO_BUCKET', 'zzdsj-files')
                return f"{protocol}://{endpoint}/{bucket}/{file_metadata.storage_path}"
            else:
                return f"/api/files/{file_metadata.file_id}"
        except Exception:
            return f"/api/files/{file_metadata.file_id}"

# 全局中间件实例
_upload_middleware = None

def get_upload_middleware() -> UnifiedFileUploadMiddleware:
    """获取统一文件上传中间件实例"""
    global _upload_middleware
    if _upload_middleware is None:
        _upload_middleware = UnifiedFileUploadMiddleware()
    return _upload_middleware

# 快捷函数
async def upload_document(file: UploadFile, **kwargs) -> Dict[str, Any]:
    """快捷文档上传函数"""
    middleware = get_upload_middleware()
    return await middleware.upload_document(file, **kwargs)

async def upload_user_file(file: UploadFile, **kwargs) -> Dict[str, Any]:
    """快捷用户文件上传函数"""
    middleware = get_upload_middleware()
    return await middleware.upload_user_file(file, **kwargs)

async def delete_document(file_id: str, **kwargs) -> Dict[str, Any]:
    """快捷文档删除函数"""
    middleware = get_upload_middleware()
    return await middleware.delete_document(file_id, **kwargs) 