"""
后台文件处理API模块
提供专门用于后台系统调用的文件上传、处理和管理接口
"""

from fastapi import APIRouter
from .routes import file_upload, file_management, knowledge_integration

# 创建后台文件API路由器
file_router = APIRouter(prefix="/file", tags=["Backend File API"])

# 注册子路由
file_router.include_router(file_upload.router, prefix="/upload", tags=["File Upload"])
file_router.include_router(file_management.router, prefix="/manage", tags=["File Management"])
file_router.include_router(knowledge_integration.router, prefix="/knowledge", tags=["Knowledge Integration"])

__all__ = ["file_router"] 