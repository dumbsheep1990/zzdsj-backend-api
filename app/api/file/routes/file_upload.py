#!/usr/bin/env python3
"""
后台文件上传接口
提供专门用于后台系统调用的文件上传功能，与v1接口保持一致的API设计
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from datetime import datetime
import json

from app.middleware.file_upload_middleware import get_upload_middleware, UnifiedFileUploadMiddleware
from app.core.deps import get_current_user_optional
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 文档上传接口 ==========

@router.post("/documents", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(..., description="上传的文档文件"),
    kb_id: str = Form(..., description="知识库ID"),
    title: str = Form(None, description="文档标题"),
    category: str = Form("general", description="文档分类"),
    auto_vectorize: bool = Form(True, description="是否自动向量化"),
    metadata: str = Form("{}", description="额外元数据(JSON字符串)"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    后台文档上传接口
    
    - 支持后台系统指定用户ID
    - 自动文件类型验证
    - 统一文件ID管理
    - 集成MinIO存储
    - 支持自动向量化
    """
    try:
        # 解析额外元数据
        try:
            extra_metadata = json.loads(metadata)
        except:
            extra_metadata = {}
        
        # 添加标题信息
        if title:
            extra_metadata["title"] = title
        
        # 确定用户ID（优先使用指定的user_id，否则使用当前用户）
        effective_user_id = user_id or (str(current_user.id) if current_user else None)
        
        # 使用统一中间件上传
        result = await middleware.upload_document(
            file=file,
            kb_id=kb_id,
            category=category,
            metadata=extra_metadata,
            auto_vectorize=auto_vectorize,
            user_id=effective_user_id
        )
        
        logger.info(f"后台文档上传: {file.filename} -> {result['file_id']}, 用户: {effective_user_id}")
        
        return {
            "success": True,
            "data": {
                "document_id": result["file_id"],  # 兼容v1接口
                "file_id": result["file_id"],
                "filename": result["filename"],
                "file_size": result["file_size"],
                "file_hash": result["file_hash"],
                "storage_path": result["storage_path"],
                "upload_time": result["upload_time"],
                "auto_vectorize": auto_vectorize,
                "file_category": result.get("file_category"),
                "category": category
            },
            "message": "文档上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后台文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")

@router.post("/documents/batch", response_model=Dict[str, Any])
async def batch_upload_documents(
    files: List[UploadFile] = File(..., description="上传的文档文件列表"),
    kb_id: str = Form(..., description="知识库ID"),
    category: str = Form("batch_upload", description="文档分类"),
    auto_vectorize: bool = Form(True, description="是否自动向量化"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    后台批量文档上传接口
    
    - 支持多文件同时上传
    - 并行处理提高效率
    - 详细的上传结果报告
    - 后台系统可指定用户ID
    """
    try:
        # 确定用户ID
        effective_user_id = user_id or (str(current_user.id) if current_user else None)
        
        # 使用统一中间件批量上传
        result = await middleware.batch_upload_documents(
            files=files,
            kb_id=kb_id,
            category=category,
            auto_vectorize=auto_vectorize,
            user_id=effective_user_id
        )
        
        logger.info(f"后台批量上传: {result['success_count']}/{result['total_files']}, 用户: {effective_user_id}")
        
        return {
            "success": result["success"],
            "data": {
                "total_files": result["total_files"],
                "success_count": result["success_count"],
                "error_count": result["error_count"],
                "results": result["results"],
                "kb_id": kb_id,
                "category": category,
                "auto_vectorize": auto_vectorize
            },
            "message": f"批量上传完成: 成功{result['success_count']}个，失败{result['error_count']}个"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后台批量文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量文档上传失败: {str(e)}")

# ========== 知识库文件上传（兼容v1接口） ==========

@router.post("/knowledge-bases/{kb_id}/documents/upload-file", response_model=Dict[str, Any])
async def upload_document_file(
    kb_id: str,
    file: UploadFile = File(..., description="上传的文档文件"),
    title: str = Form(..., description="文档标题"),
    tags: str = Form("[]", description="文档标签（JSON字符串）"),
    category: str = Form("", description="文档分类"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    后台知识库文档上传接口（兼容v1格式）
    
    与 /api/v1/knowledge-bases/{kb_id}/documents/upload-file 保持兼容
    """
    try:
        # 解析标签
        try:
            tags_list = json.loads(tags) if tags else []
        except:
            tags_list = []
        
        # 准备元数据
        metadata = {
            "title": title,
            "category": category,
            "tags": tags_list,
            "source_api": "backend_knowledge_base_upload"
        }
        
        # 确定用户ID
        effective_user_id = user_id or (str(current_user.id) if current_user else None)
        if effective_user_id:
            metadata["uploaded_by"] = effective_user_id
        
        # 使用统一中间件上传
        result = await middleware.upload_document(
            file=file,
            kb_id=kb_id,
            metadata=metadata,
            auto_vectorize=True,
            user_id=effective_user_id
        )
        
        logger.info(f"后台知识库文档上传: {file.filename} -> {result['file_id']}, 知识库: {kb_id}")
        
        return {
            "success": True,
            "data": {
                "document_id": result["file_id"],  # 兼容v1字段
                "file_id": result["file_id"],
                "filename": result["filename"],
                "file_name": result["filename"],  # 兼容v1字段
                "chunks": [],  # TODO: 集成切分结果
                "file_size": result["file_size"],
                "file_hash": result["file_hash"],
                "storage_path": result["storage_path"],
                "upload_time": result["upload_time"],
                "title": title,
                "category": category,
                "tags": tags_list
            },
            "message": "文件上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后台知识库文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

# ========== 通用文件上传接口 ==========

@router.post("/generic", response_model=Dict[str, Any])
async def upload_generic_file(
    file: UploadFile = File(..., description="上传的文件"),
    folder: str = Form("generic", description="存储文件夹"),
    max_size_mb: int = Form(100, description="最大文件大小(MB)"),
    allowed_types: str = Form("[]", description="允许的文件类型（JSON字符串）"),
    user_id: str = Form(None, description="用户ID（后台调用时可指定）"),
    metadata: str = Form("{}", description="额外元数据(JSON字符串)"),
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware),
    current_user: User = Depends(get_current_user_optional)
):
    """
    后台通用文件上传接口
    
    - 支持任意类型文件上传
    - 灵活的文件类型限制
    - 自定义存储文件夹
    - 后台系统可指定用户ID
    """
    try:
        # 解析允许的文件类型
        try:
            allowed_types_list = json.loads(allowed_types) if allowed_types else None
        except:
            allowed_types_list = None
        
        # 解析额外元数据
        try:
            extra_metadata = json.loads(metadata)
        except:
            extra_metadata = {}
        
        # 确定用户ID
        effective_user_id = user_id or (str(current_user.id) if current_user else None)
        
        # 添加后台调用标识
        extra_metadata.update({
            "source": "backend_api",
            "folder": folder,
            "uploaded_via": "backend_generic_upload"
        })
        
        # 使用统一中间件上传用户文件
        result = await middleware.upload_user_file(
            file=file,
            folder=folder,
            user_id=effective_user_id,
            allowed_types=allowed_types_list,
            max_size_mb=max_size_mb
        )
        
        logger.info(f"后台通用文件上传: {file.filename} -> {result['file_id']}, 文件夹: {folder}")
        
        return {
            "success": True,
            "data": {
                "file_id": result["file_id"],
                "filename": result["filename"],
                "file_url": result["file_url"],
                "file_size": result["file_size"],
                "content_type": result["content_type"],
                "upload_time": result["upload_time"],
                "folder": folder,
                "metadata": extra_metadata
            },
            "message": "文件上传成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"后台通用文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

# ========== 文件信息查询接口 ==========

@router.get("/info/{file_id}", response_model=Dict[str, Any])
async def get_file_info(
    file_id: str,
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware)
):
    """
    获取文件信息
    
    - 统一的文件信息查询
    - 包含存储状态和元数据
    - 支持后台系统调用
    """
    try:
        file_info = middleware.get_file_info(file_id)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return {
            "success": True,
            "data": file_info,
            "message": "获取文件信息成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")

@router.get("/supported-types", response_model=Dict[str, Any])
async def get_supported_file_types(
    middleware: UnifiedFileUploadMiddleware = Depends(get_upload_middleware)
):
    """
    获取支持的文件类型
    
    - 返回所有支持的文件类型
    - 按分类组织
    - 用于后台系统参考
    """
    try:
        supported_types = middleware.get_supported_types()
        
        return {
            "success": True,
            "data": supported_types,
            "message": "获取支持的文件类型成功"
        }
        
    except Exception as e:
        logger.error(f"获取支持的文件类型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取支持的文件类型失败: {str(e)}")

# ========== 健康检查接口 ==========

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    后台文件上传服务健康检查
    """
    try:
        return {
            "success": True,
            "data": {
                "service": "backend_file_upload",
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "features": [
                    "document_upload",
                    "batch_upload", 
                    "knowledge_integration",
                    "generic_file_upload",
                    "unified_file_management"
                ]
            },
            "message": "后台文件上传服务运行正常"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail="服务健康检查失败") 